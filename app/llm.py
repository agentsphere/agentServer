
from enum import Enum
import json
import os
from typing import Annotated, Optional
import httpx
import litellm
from pydantic import BaseModel, Field, conint

import logging

logger = logging.getLogger(__name__)
TOKEN=os.getenv("TOKEN")

MODEL="ollama_chat/qwen2.5-coder:32b"

class DifficultyLevel(str, Enum):
    """Enum representing different levels of difficulty."""
    EASY = "easy"
    MEDIUM = "medium"
    COMPLEX = "complex"

class CategoryResponse(BaseModel):
    """
    Represents the response model for a category classification.
    """

    lvl: DifficultyLevel = Field(description="The difficulty level of the category.")
    certainty: Annotated[int, Field(ge=0, le=10, description="A confidence score between 0 and 10 indicating the certainty of the classification. 0 = really uncertain, 10 = really certain. If the value is below 6, another Agent will check.")]

class Message(BaseModel):
    role: str
    content: str

class Roles(str, Enum):
    SYSTEM = "system"
    USER = "user"

def categorizeRequest(request: str):
    """
    Categorizes a Request using LLM
    """

    logger.info(f"Categorize Request {request}")
    model="ollama_chat/qwen2.5-coder:32b"

    response = litellm.completion(
        model=model,
        response_format = CategoryResponse, 
        messages=[
            Message(role=Roles.SYSTEM.value, content=f"Categorize response, according to format: {CategoryResponse.__doc__}").model_dump(),
            Message(role=Roles.USER.value, content=f'''Categorize following request, easy: able to answer right away. medium: requires special background but can be done by one. complex: Team is required, multiple roles are involved.  if you are uncertain a seconds Agent will check to confirm your category:
                    {request}
            ''').model_dump()
        ],

    )
    logger.debug(f"respone {response}")

    content = response.choices[0].message.content
    logger.debug(f"content {content}")
    c = CategoryResponse.model_validate(json.loads(content))

    logger.debug(f"c {c}")
    return c

def answerRequest(request: str):
    """
    Categorizes a Request using LLM
    """

    logger.info(f"Answer Request {request}")
    model="ollama_chat/qwen2.5-coder:32b"

    response = litellm.completion(
        model=model,
        messages=[
            Message(role=Roles.SYSTEM.value, content=f"Answer Request").model_dump(),
            Message(role=Roles.USER.value, content=f'''Answer Request to the best of your knowledge
                    {request}
            ''').model_dump()
        ],

    )
    logger.debug(f"respone {response}")

    content = response.choices[0].message.content
    logger.debug(f"content {content}")

    return content



class Agent(BaseModel):
    """
    Represents an agent with a specific role, background, skill set, and available tools.
    """

    role: str = Field(description="The primary role or job function of the agent.")
    background: str = Field(description="A brief background of the agent, including experience and expertise.")
    skills: str = Field(description="A list of key skills that the agent possesses.")
    tools: str = Field(description="A list of tools or technologies that the agent is proficient in.")


class AgentWorking(BaseModel):
    """
    Represents an agent's working state, including tools used and the final answer generated.
    """

    toolsToCall: str = Field(description="A list of tools or services the agent needs to call or interact with. In the Format [tool1(parameters), tool2(params)]")
    finalAnswer: str = Field(description="The final response or conclusion provided by the agent after processing.")


class Task(BaseModel):
    """
    Represents a single task with rollback instructions, a description, and a test.
    """

    rollback: str = Field(description="Instructions to revert the task if needed.")
    description: str = Field(description="A detailed explanation of what the task entails.")
    test: str = Field(description="A test or validation method to ensure the task is completed correctly.")
    tool_queries: list[str] = Field(description="A list of tool quereies which might be needed to solve the task. prefer command lines or API calls over UI/Browser tools. Like ['clone git repo', 'list files', 'list directories', 'git commit']")
    context: str = Field(description="Context Information like repo urls, documentation, company programming guidelines")

class Tasks(BaseModel):
    """
    Represents a collection of tasks.
    """

    tasks: list[Task] = Field(description="A list of individual tasks to be executed.")

class SolveTask(BaseModel):
    tool_calls: list[str] = Field(description="List of Tool calls in the format tool(param1, param2)")



class ToolSuggestionRequest(BaseModel):
    """Represents a request for tool suggestions based on a query and parameters."""
    #user: Optional[User] = None
    #token: str
    queries: list[str]


def solveTask(agent:Agent, task: Task):
   #load_tools
    logger.info(f"task {task}")
    with httpx.Client() as client:
        data = ToolSuggestionRequest(queries=task.tool_queries)
        url = 'http://127.0.0.1:8000/tools/suggestions'  # Example URL that echoes the posted data
        logger.info(f"Sending execution request: {data.model_dump_json()}")

        response = client.post(url, data=data.model_dump_json(),headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})  # ✅ Correct async call)  # ✅ Correct async call
        
    response = litellm.completion(
        model=MODEL,
        response_format=SolveTask,
        messages=[
            Message(role=Roles.SYSTEM.value, content=f"You are: {agent.model_dump()}").model_dump(),
            Message(role=Roles.USER.value, content=f'''Tools available 
                    {response.json} 

                    Context Informtion: {task.context}
                    Based on who you are, your background skills and tools, solve the current task:
                    {task.description}
            ''').model_dump()
        ],
    )
    content = response.choices[0].message.content
    logger.info(f"content {content}") # expecting tool call here

 

def solveMediumRequest(request: str):
    """Solves a Request Medium complexity"""

    logger.info(f"solveMediumRequest {request}")
    model="ollama_chat/qwen2.5-coder:32b"

    response = litellm.completion(
        model=model,
        response_format=Agent,
        messages=[
            Message(role=Roles.SYSTEM.value, content=f"You are a Manager").model_dump(),
            Message(role=Roles.USER.value, content=f'''Based on the following request, which schould be of medium complexity, which means a single agent can solve it with the appropriate background, skills and tools. Determine which role, skill, background and tool might be needed. Request:
                    {request}
            ''').model_dump()
        ],
    )
    logger.debug(f"respone {response}")

    content = response.choices[0].message.content

    logger.debug(f"content {content}")
    c = Agent.model_validate(json.loads(content))
    logger.info(f"Agent {c}")

    # Gather information

    response = litellm.completion(
        model=model,
        response_format=Tasks,
        messages=[
            Message(role=Roles.SYSTEM.value, content=f"You are: {c.model_dump()}").model_dump(),
            Message(role=Roles.USER.value, content=f'''Based on who you are, your background skills and tools. Analyse the request and break it down into multiple executable tasks, including tasks to test if the request is fullfilled, including steps to rollback to be able to revert if something goes wrong. Always consider Best practices for the considered tool and workflow you use. Request:
                    {request}
            ''').model_dump()
        ],
    )
    currentTasks= response.choices[0].message.content

    response = litellm.completion(
        model=model,
        response_format=Tasks,
        messages=[
            Message(role=Roles.SYSTEM.value, content=f"You are: {c.model_dump()}").model_dump(),
            Message(role=Roles.USER.value, content=f'''Context: 
                    Original Request: {request}
                    
                    currentTasks: {currentTasks}
                    
                    Based on who you are, your background skills and tools. Analyse the currentTasks if they are executcable steps to solve the given original Request. Improve the given tasks. If the rollback is not needed leave it blank, make the tool queries concise and favour bash, sh, cli calls and mentiond the bash, sh, cli within the tool queries whenever used. Always consider Best practices for the considered tool and workflow you use (i.e. if your all dealing with code use git repo, never push to main use PRs and so on). Request:
                    {request}
            ''').model_dump()
        ],
    )

    logger.debug(f"solve reponse {response}")
    content = response.choices[0].message.content
    logger.info(f"Tasks {content}")

    tasks = Tasks.model_validate(json.loads(content))
    for task in tasks.tasks:
        solveTask(agent=c, task=task)
      

        
    return content
