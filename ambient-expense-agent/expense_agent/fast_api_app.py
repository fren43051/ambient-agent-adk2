import os
import json
import logging
from fastapi import FastAPI, Request
from google.adk.cli.fast_api import get_fast_api_app

from expense_agent.app_utils.telemetry import setup_telemetry
from expense_agent.app_utils.typing import Feedback

setup_telemetry()

# Use standard Python logging for console logs instead of google_cloud_logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
session_service_uri = None
artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=False,  # Disabled per checklist
    trigger_sources=["pubsub"]  # Enable Pub/Sub triggers
)
app.title = "ambient-expense-agent"
app.description = "API for interacting with the Agent ambient-expense-agent"

# Middleware to normalize the Pub/Sub subscription name down to a short name
@app.middleware("http")
async def normalize_pubsub_subscription(request: Request, call_next):
    if request.url.path.endswith("/trigger/pubsub") and request.method == "POST":
        body = await request.body()
        if body:
            try:
                payload = json.loads(body)
                if "subscription" in payload:
                    full_sub = payload["subscription"]
                    # Extract just the short name
                    payload["subscription"] = full_sub.split("/")[-1]
                    
                new_body = json.dumps(payload).encode("utf-8")
                
                async def receive():
                    return {"type": "http.request", "body": new_body}
                
                request._receive = receive
            except Exception as e:
                logger.error(f"Error normalizing pubsub subscription: {e}")
                
    response = await call_next(request)
    return response

@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    logger.info(f"Feedback received: {feedback.model_dump()}")
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    # Serving on port 8080 as requested
    uvicorn.run(app, host="0.0.0.0", port=8080)
