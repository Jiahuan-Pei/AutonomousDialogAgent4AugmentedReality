import os
from typing import Tuple, Dict, List
import inspect
import asyncio

from langchain.agents import initialize_agent, Tool
from langchain.tools import StructuredTool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.prompts.chat import MessagesPlaceholder
from langchain.callbacks.manager import CallbackManager
import tools_wrappers

from langchain.callbacks.base import AsyncCallbackHandler

from dotenv import load_dotenv, find_dotenv
# load environment variables in .env file
load_dotenv(find_dotenv())

working_directory = os.getenv("WORKING_DIRECTORY")
# Change the working directory
if working_directory:
    os.chdir(os.getenv("WORKING_DIRECTORY"))


class Config:
    """
    Contains the configuration of the LLM.
    """
    model = 'gpt-3.5-turbo-16k-0613'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    temperature = 0.0
    verbose = True
    print(f'OPENAI_API_KEY={OPENAI_API_KEY}')


def setup_memory() -> Tuple[Dict, ConversationBufferMemory]:
    """
    Sets up memory for the open ai functions agent.
    :return a tuple with the agent keyword pairs and the conversation memory.
    """
    agent_kwargs = {
        "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")],
    }
    memory = ConversationBufferMemory(memory_key="memory", return_messages=True)

    return agent_kwargs, memory


# In the setup_tools function, access descriptions from LegoAPIWrapper
def setup_tools() -> List[StructuredTool]:
    lego_toolkits = tools_wrappers.LegoAPIWrapper()

    # Get a list of all callable methods in the LegoAPIWrapper instance
    tools = [method for method in dir(lego_toolkits) if callable(getattr(lego_toolkits, method)) and not method.startswith("_")]

    # Create StructuredTool objects with descriptions from LegoAPIWrapper
    structured_tools = [
        StructuredTool.from_function(getattr(lego_toolkits, func), name=func, description=lego_toolkits.descriptions.get(func, ""))
        for func in tools
    ]

    return structured_tools


def setup_agent(client_in_the_loop=False, **kwargs) -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    cfg = Config()

    if client_in_the_loop:
        llm = ChatOpenAI(
            temperature=cfg.temperature,
            model=cfg.model,
            verbose=cfg.verbose,
            streaming=True,  # Pass `streaming=True` to make sure the client receives the data.
            callback_manager=CallbackManager(
                [AsyncCallbackHandler]
            ),  # Pass the callback handler
        )
    else:
        llm = ChatOpenAI(
            temperature=cfg.temperature,
            model=cfg.model,
            verbose=cfg.verbose
        )

    agent_kwargs, memory = setup_memory()

    tools = setup_tools()

    return initialize_agent(
        tools, 
        llm,
        agent=AgentType.OPENAI_FUNCTIONS, 
        verbose=False, 
        agent_kwargs=agent_kwargs,
        memory=memory
    )