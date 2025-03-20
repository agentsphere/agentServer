import asyncio

import datetime
import os
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Request, HTTPException,status
from pydantic import BaseModel
import httpx
import logging
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from app.llm import categorizeRequest, answerRequest, solveMediumRequest
# Load variables from .env file
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


import uvicorn

import os
import requests

from fastapi import HTTPException, Header, Depends, status


def introspect_token(token: str) -> dict:
    if token is None: 
       raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token introspection failed"
        ) 
    ctoken = token.split(" ", 1)[1] if token.startswith("Bearer ") else token
    introspection_url = "https://auth.agentsphere.cloud/realms/agentsphere/protocol/openid-connect/token/introspect"

    client_id = "agentserver"
    client_secret = os.getenv("CLIENT_SECRET")

    logger.debug(f"id {client_id} sec {client_secret}")
    response = requests.post(
        introspection_url,
        headers={"Content-Type":"application/x-www-form-urlencoded"},
        data={"token": ctoken, "client_id": client_id, "client_secret": client_secret}
    )
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token introspection failed"
        )


from pydantic import BaseModel, Field

class User(BaseModel):
    id: Optional[str] 
    role: Optional[str] 
    username: Optional[str]
    mail: Optional[str]
    token: Optional[str]


def get_user_headers(
    user_id: Optional[str] = Header(None, alias="X-OpenWebUI-User-Id"),
    user_role: Optional[str] = Header(None, alias="X-OpenWebUI-User-Role"),
    user_name: Optional[str] = Header(None, alias="X-OpenWebUI-User-Name"),
    user_email: Optional[str] = Header(None, alias="X-OpenWebUI-User-Email"),
    token: Optional[str] = Header(None, alias="Authorization")
):
    return {
        "id": user_id,
        "role": user_role,
        "username": user_name,
        "mail": user_email,
        "token": token
    }


def get_user(user_headers: dict = Depends(get_user_headers)):
    introspect_token(user_headers.get("token", None))
    return User(**user_headers)

def validate_token(token_header: dict = Depends(get_user_headers)):
    introspect_token(token_header.get("token", None))
    return


logger=logging.getLogger(__name__)

app = FastAPI()
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False

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



@app.get("/api/tags", response_model=Dict[str, List[Model]])
def list_models(token: str = Depends(validate_token)):
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
def get_version(token: str = Depends(validate_token)):
    return {"version": "0.5.7"}

from datetime import datetime, timezone, timedelta
tz_offset = -8  # Offset in hours
tzinfo = timezone(timedelta(hours=tz_offset))

def getResponseObject(message: str):
    return {
        "model": "superman",
        "created_at": f"{datetime.now(tzinfo)}",
        "message": {
            "role": "assistant",
            "content": f"{message}"
        },
        "done": True,
        "total_duration": 2,
        "load_duration": 2,
        "prompt_eval_count": 2,
        "prompt_eval_duration": 2,
        "eval_count": 2,
        "eval_duration": 2
    }



@app.post("/api/chat")
def handle_models(request: ChatRequest,token: str = Depends(get_user)):
    # Extract the user's message content±
    #user_content = request.messages[0].content

    # Process the request using the supermanPrepare.kickoff function
    #result_prepare = supermanPrepare.kickoff(inputs={"request": user_content})

    # Construct the response

    # categorize requesti
    logger.debug(f"request {request}")
    userRequest=request.messages[0].content
    response = categorizeRequest(userRequest)

    if response.lvl.value == "easy":
        return getResponseObject(f"Not worthy of my time but hey: {answerRequest(userRequest)}")
    elif response.lvl.value=="complex" or response.lvl.value == "medium":
        logger.info("medium")
        return getResponseObject(f"we are getting there. wanna give me something difficult? {solveMediumRequest(userRequest)}")

    return getResponseObject("Not yet")


PORT = int(os.getenv("PORT",8080))  # Define a default port

async def run():
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, loop="asyncio")
    server = uvicorn.Server(config)

    logging.info(f"Starting server on http://127.0.0.1:{PORT}")
    
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Server shutdown requested. Exiting cleanly.")


