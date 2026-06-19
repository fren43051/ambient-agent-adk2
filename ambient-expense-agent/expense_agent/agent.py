import base64
import json
import re
from typing import Any

from google.adk.workflow import Workflow, node
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from pydantic import BaseModel
from google.genai import types

from .config import config

class Expense(BaseModel):
    amount: float
    submitter: str
    category: str
    description: str
    date: str

class RiskReport(BaseModel):
    risk_level: str
    reasoning: str

@node
def parse_input(node_input: Any) -> Event:
    """Parses incoming JSON or PubSub payload into an Expense."""
    data_dict = {}
    
    if isinstance(node_input, dict):
        data_dict = node_input
    elif hasattr(node_input, "parts") and node_input.parts and node_input.parts[0].text:
        try:
            data_dict = json.loads(node_input.parts[0].text)
        except json.JSONDecodeError:
            pass
    elif isinstance(node_input, str):
        try:
            data_dict = json.loads(node_input)
        except json.JSONDecodeError:
            pass

    # Extract the 'data' payload
    data_content = data_dict.get("data")
    if isinstance(data_content, str):
        # Try to base64 decode if it's a pubsub message
        try:
            decoded = base64.b64decode(data_content).decode("utf-8")
            data_content = json.loads(decoded)
        except Exception:
            pass
            
    if not isinstance(data_content, dict):
        data_content = data_dict # fallback to top-level if data key isn't a dict

    expense = Expense(**data_content)
    # Put the parsed expense into the state to make it available to all nodes
    return Event(output=expense, state={"expense": expense.model_dump()})

@node
def rule_engine(node_input: Expense) -> Event:
    """Routes the expense based on the amount threshold."""
    if node_input.amount < config.threshold:
        return Event(output=node_input, route="auto_approve")
    else:
        return Event(output=node_input, route="manual_review")

@node
def auto_approve(node_input: Expense) -> Event:
    """Auto-approves expenses under the threshold."""
    decision = f"Auto-approved expense for ${node_input.amount} from {node_input.submitter}."
    return Event(
        output={"decision": "Approved", "reason": decision},
        content=types.Content(role="model", parts=[types.Part.from_text(text=decision)])
    )

# --- NEW SECURITY NODES ---
SSN_REGEX = r'\b\d{3}-\d{2}-\d{4}\b'
CC_REGEX = r'\b(?:\d[ -]*?){13,16}\b'
INJECTION_KEYWORDS = ["ignore", "bypass", "instruction", "system prompt", "approve"]

@node
def security_checkpoint(node_input: Expense, ctx: Context) -> Event:
    description = node_input.description
    redacted_categories = []
    
    # Scrub SSN
    if re.search(SSN_REGEX, description):
        description = re.sub(SSN_REGEX, "[REDACTED_SSN]", description)
        redacted_categories.append("SSN")
        
    # Scrub CC
    if re.search(CC_REGEX, description):
        description = re.sub(CC_REGEX, "[REDACTED_CC]", description)
        redacted_categories.append("Credit Card")
        
    node_input.description = description
    
    # Update context state with scrubbed expense and redactions
    ctx.state["expense"] = node_input.model_dump()
    ctx.state["redacted_categories"] = redacted_categories
    
    # Prompt injection check
    desc_lower = description.lower()
    if any(keyword in desc_lower for keyword in INJECTION_KEYWORDS):
        return Event(output=node_input, route="security_flag")
        
    return Event(output=node_input, route="safe")

@node
def security_flag_handler(node_input: Expense) -> RiskReport:
    """Formats a security event as a RiskReport to send to the human_approval node."""
    return RiskReport(
        risk_level="Critical",
        reasoning="SECURITY EVENT: Potential prompt injection or rule bypass attempt detected. Model was bypassed."
    )
# ---------------------------

risk_reviewer = LlmAgent(
    name="risk_reviewer",
    model=config.model,
    instruction=(
        "You are a financial risk reviewer. Evaluate the following expense "
        "and determine if there are any risks or policy violations. "
        "Provide a risk_level (Low, Medium, High) and your reasoning."
    ),
    output_schema=RiskReport,
    output_key="risk_report"
)

@node
def human_approval(ctx: Context, node_input: RiskReport) -> Any:
    """Pauses for human approval using RequestInput."""
    if not ctx.resume_inputs:
        expense = ctx.state.get("expense", {})
        message = (
            f"Please review the expense for {expense.get('submitter', 'unknown')} "
            f"amounting to ${expense.get('amount', 0)}. \n"
            f"Risk Assessment: {node_input.risk_level} - {node_input.reasoning}\n\n"
            "Do you 'approve' or 'reject'?"
        )
        yield RequestInput(interrupt_id="approve_expense", message=message)
        return
        
    human_decision = ctx.resume_inputs.get("approve_expense", "reject")
    yield Event(output=human_decision)

@node
def record_outcome(node_input: str, ctx: Context) -> Event:
    """Records the final decision (Approve/Reject)."""
    expense = ctx.state.get("expense", {})
    decision_msg = f"Final Decision: {node_input} for ${expense.get('amount')} expense from {expense.get('submitter')}."
    return Event(
        output={"decision": node_input, "details": decision_msg},
        content=types.Content(role="model", parts=[types.Part.from_text(text=decision_msg)])
    )

# Wire up the workflow graph
root_agent = Workflow(
    name="expense_approval_workflow",
    edges=[
        ('START', parse_input),
        (parse_input, rule_engine),
        (rule_engine, {"auto_approve": auto_approve, "manual_review": security_checkpoint}),
        (security_checkpoint, {"safe": risk_reviewer, "security_flag": security_flag_handler}),
        (security_flag_handler, human_approval),
        (risk_reviewer, human_approval),
        (human_approval, record_outcome),
    ]
)

app = App(name="expense_agent", root_agent=root_agent)
