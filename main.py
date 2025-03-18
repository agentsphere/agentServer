
import asyncio
import datetime
import os
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Request, HTTPException,status
from pydantic import BaseModel
import httpx
import logging

import uvicorn

logger=logging.getLogger(__name__)

app = FastAPI()
TOKEN="7ajauszqwmdhjg.ax9"
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]

def verify(token: str):
    logger.debug(f"token {token}")
    if token != TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return None  # This returns the user data from the token

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)):
    verify(token)
    return   


#OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Ollama server URL
@app.middleware("http")
async def log_request_headers(request: Request, call_next):
    headers = {k: v for k, v in request.headers.items()}
    logger.info(f"Incoming {request.method} request to {request.url.path} with headers: {headers}")
    response = await call_next(request)
    return response

class ModelDetails(BaseModel):
    format: str
    family: str
    families: Optional[List[str]] = None
    parameter_size: str
    quantization_level: str

class Model(BaseModel):
    name: str
    model: str
    modified_at: datetime.datetime
    size: int
    digest: str
    details: ModelDetails

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False


@app.get("/api/tags", response_model=Dict[str, List[Model]])
def list_models(token: str = Depends(get_current_user)):
    return {
        "models": [
            {
                "name": "superman:latest",
                "model": "superman:latest",
                "modified_at": "2023-12-07T09:32:18.757212583-08:00",
                "size": 3825819519,
                "digest": "fe938a131f40e6f6d40083c9f0f430a515233eb2edaa6d72eb85c50d64f2300e",
                "details": {
                    "format": "gguf",
                    "family": "llama",
                    "families": None,
                    "parameter_size": "7B",
                    "quantization_level": "Q4_0"
                }
            }
        ]
    }

@app.get("/api/version")
def get_version(token: str = Depends(get_current_user)):
    return {"version": "0.5.7"}


@app.post("/api/chat")
def handle_models(request: ChatRequest,token: str = Depends(get_current_user)):
    # Extract the user's message content
    #user_content = request.messages[0].content

    # Process the request using the supermanPrepare.kickoff function
    #result_prepare = supermanPrepare.kickoff(inputs={"request": user_content})

    # Construct the response
    return {
        "model": "superman",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "message": {
            "role": "assistant",
            "content": "result_prepare"
        },
        "done": True,
        "total_duration": 5191566416,
        "load_duration": 2154458,
        "prompt_eval_count": 26,
        "prompt_eval_duration": 383809000,
        "eval_count": 298,
        "eval_duration": 4799921000
    }

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

PORT = int(os.getenv("PORT",8031))  # Define a default port

async def run():
    """Runs FastAPI server properly inside an async event loop"""
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, loop="asyncio")
    server = uvicorn.Server(config)

    logging.info(f"Starting server on http://127.0.0.1:{PORT}")
    
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Server shutdown requested. Exiting cleanly.")




