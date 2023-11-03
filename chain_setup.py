import os
from typing import Tuple, Dict, List

from langchain.agents import initialize_agent
from langchain.tools import StructuredTool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.prompts.chat import MessagesPlaceholder

from langchain.chains import LLMChain

from langchain.prompts import ChatPromptTemplate
from langchain.prompts import HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain.schema.messages import SystemMessage

from langchain.callbacks.manager import CallbackManager
import tools_wrappers
import asyncio
from langchain.callbacks.streaming_stdout_final_only import (
    FinalStreamingStdOutCallbackHandler,
)

from fastapi import WebSocket


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
    system_message = SystemMessage(
        content="""
        You are a helpful AI assistant who aim to train the user how to assemble a LEGO car in XR immersive system.
        Extended Reality (XR) directs to the assortment of Virtual Reality (VR), Augmented Reality (AR), and Mixed Reality (MR).
        Please make sure you complete the objective above with the following rules:
        1/ The user is a trainee who is wearing HoloLen 2 glasses and is able to see XR environments in realtime.
        2/ You are able to call Unity functions in the LEGO AR application.
        3/ You are able to obtain HoloLens 2 Sensor Streaming data via TCP.
        4/ Alert if the user ask you something outside of LEGO assembly task but do not give overconfident answers.
        Your task is to answer the user's questions and assist the user to understand how to complete LEGO assembly task in XR. 
        """
    )
    agent_kwargs = {
        "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")],
        "system_message": system_message,
    }
    memory = ConversationBufferMemory(memory_key="memory", return_messages=True)

    return agent_kwargs, memory


# In the setup_tools function, access descriptions from LegoAPIWrapper
def setup_tools(loop=None) -> List[StructuredTool]:
    lego_toolkits = tools_wrappers.LegoAPIWrapper(loop)     # async toolkits

    # Get a list of all callable methods in the LegoAPIWrapper instance
    tools = [method for method in dir(lego_toolkits) if callable(getattr(lego_toolkits, method)) and not method.startswith("_")]

    # Create StructuredTool objects with descriptions from LegoAPIWrapper
    structured_tools = [
        StructuredTool.from_function(getattr(lego_toolkits, func), name=func, description=lego_toolkits.descriptions.get(func, ""))
        for func in tools
    ]

    return structured_tools


def setup_agent_streaming(**kwargs) -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    cfg = Config()

    # streaming_handler = AsyncCallbackHandler
    llm = ChatOpenAI(
        temperature=cfg.temperature,
        model=cfg.model,
        verbose=cfg.verbose,
        streaming=True,  # ! Important: Pass `streaming=True` to make sure the client receives the data.
        callbacks=[FinalStreamingStdOutCallbackHandler(
            answer_prefix_tokens=['Answer']
        )], # ! Important:
        # callbacks = [FinalStreamingStdOutCallbackHandler()]  # ! Important:
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


def setup_agent(loop=None) -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    cfg = Config()

    llm = ChatOpenAI(
        temperature=cfg.temperature,
        model=cfg.model,
        verbose=cfg.verbose
    )

    agent_kwargs, memory = setup_memory()

    tools = setup_tools(loop)

    return initialize_agent(
        tools, 
        llm,
        agent=AgentType.OPENAI_FUNCTIONS, 
        verbose=False, 
        agent_kwargs=agent_kwargs,
        memory=memory
    )