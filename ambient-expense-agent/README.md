# Ambient Expense Agent (ADK 2.0)

This repository contains an **Ambient Expense Approval Agent** built using the Google Agent Development Kit (ADK) 2.0.

## Overview
This is an event-driven AI agent that operates asynchronously in the background. It listens to incoming Pub/Sub messages (expense payloads) via a FastAPI endpoint, routes them through a LangGraph workflow, and makes autonomous decisions to approve or reject expenses based on predefined policies.

### Key Features
- **Ambient / Event-Driven:** Triggered by Pub/Sub messages via HTTP POST instead of a traditional chat interface.
- **Human-in-the-Loop (HITL):** Automatically pauses execution and waits for human review if a high-risk expense or prompt injection is detected.
- **Prompt Injection Defense:** Uses an LLM to pre-evaluate the description for malicious instructions (e.g., "ignore all previous instructions").
- **PII Redaction:** Automatically detects and redacts sensitive information (like SSN or Credit Card numbers) before the payload ever reaches the primary LLM, protecting data privacy.

## Project Structure
- `expense_agent/agent.py`: The core ADK LangGraph workflow containing the logic, security checkpoints, and the LLM node.
- `expense_agent/fast_api_app.py`: A FastAPI server that exposes the `/trigger/pubsub` endpoint to ingest events and dispatch them to the ADK session manager.
- `Makefile`: Commands to quickly spin up the environment (`make install`, `make playground`, `make ambient_server`).

## Running Locally

1. **Install Dependencies:**
   ```bash
   uv sync
   ```

2. **Run the Ambient Server:**
   ```bash
   uv run python -m expense_agent.fast_api_app
   ```
   The server will start on port `8080` and expose the `/trigger/pubsub` endpoint.

3. **View the Developer UI:**
   Open your browser to:
   `http://localhost:8080/dev-ui/`
   This interface allows you to view active sessions, inspect the execution graph, and provide human input for paused sessions.

## Testing with Pub/Sub Payloads
You can test the agent by sending HTTP POST requests to `http://localhost:8080/apps/expense_agent/trigger/pubsub`. The request body must be a valid Pub/Sub message with a base64 encoded data payload.

Example Payload (Auto-Approval):
```json
{
  "message": {
    "data": "eyJhbW91bnQiOiA0NSwgInN1Ym1pdHRlciI6ICJib2JAY29tcGFueS5jb20iLCAiY2F0ZWdvcnkiOiAibWVhbHMiLCAiZGVzY3JpcHRpb24iOiAiVGVhbSBsdW5jaCIsICJkYXRlIjogIjIwMjYtMDQtMTIifQ=="
  },
  "subscription": "projects/my-project/subscriptions/test-sub"
}
```

## Security & Credentials
- **No hardcoded API keys are included in this repository.** 
- The project is configured to use Google Cloud Application Default Credentials (ADC) via `GOOGLE_GENAI_USE_ENTERPRISE="TRUE"` in the local environment.
