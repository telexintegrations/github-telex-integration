import logging
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks
import json

from config import integration_config
from github_utils import verify_github_signature, create_telex_payload
from telex_utils import send_to_telex

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="GitHub to Telex Integration")

@app.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header("unknown")
):
    logging.info("Received webhook event")
    
    # Retrieve and verify the GitHub signature header
    body = await request.body()
    if not x_hub_signature_256:
        logging.error("Missing GitHub signature header")
        raise HTTPException(status_code=400, detail="Missing GitHub signature header")
    
    if not verify_github_signature(body, x_hub_signature_256, integration_config.github_secret):
        logging.error("Invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Parse the JSON payload
    try:
        payload = await request.json()
    except Exception:
        logging.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Prepare the payload for Telex
    telex_payload = create_telex_payload(x_github_event, payload)
    logging.info(f"Telex payload: {telex_payload}")
    
    # Send to Telex in the background
    background_tasks.add_task(send_to_telex, telex_payload)
    
    logging.info("Event processed and queued for forwarding to Telex")
    return {"detail": "Event processed and forwarded to Telex"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)