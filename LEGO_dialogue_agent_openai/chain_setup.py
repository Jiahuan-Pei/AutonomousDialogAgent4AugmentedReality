from langchain.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain.utilities.wikipedia import WikipediaAPIWrapper
from langchain.utilities import PubMedAPIWrapper
from langchain import ArxivAPIWrapper, LLMMathChain
from langchain.agents import initialize_agent, Tool
from langchain.tools import StructuredTool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory

from langchain.prompts.chat import MessagesPlaceholder
import tools_wrappers
from typing import Tuple, Dict

import os

# from dotenv import load_dotenv, find_dotenv
# # load environment variables in .env file
# load_dotenv(find_dotenv())


class Config():
    """
    Contains the configuration of the LLM.
    """
    model = 'gpt-3.5-turbo-16k-0613'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    print(f'OPENAI_API_KEY={OPENAI_API_KEY}')
    llm = ChatOpenAI(temperature=0, model=model)


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


def setup_agent() -> AgentExecutor:
    """
    Sets up the tools for a function based chain.
    """
    cfg = Config()

    lego_toolkits = tools_wrappers.LegoAPIWrapper()  # a set of customized LEGO tools

    tools = [
        StructuredTool.from_function(
            func=lego_toolkits.callStartAssemble,
            name='callStartAssemble',
            description='Useful tool for calling LEGO AR system to initiate the assembly process.'
        ),
        StructuredTool.from_function(
            func=lego_toolkits.callNextStep,
            name='callNextStep',
            description='Useful tool for calling LEGO AR system to move to the next assembly step.'
        ),
        StructuredTool.from_function(
            func=lego_toolkits.callFrontStep,
            name='callFrontStep',
            description='Useful tool for calling LEGO AR system to go back to the previous assembly step.'
        ),
        StructuredTool.from_function(
            func=lego_toolkits.callExplode,
            name='callExplode',
            description='Useful tool for calling LEGO AR system to trigger an explosion for detailed viewing.'
        ),
        StructuredTool.from_function(
            func=lego_toolkits.callRecover,
            name='callRecover',
            description='Useful tool for calling LEGO AR system to restore the initial state of the VR objects after explosion.'
        ),
        StructuredTool.from_function(
            func=lego_toolkits.callFinishedVideo,
            name='callFinishedVideo',
            description='Useful tool for calling LEGO AR system to end the assembly process and show a video of the assembled LEGO bricks.'
        ),
        StructuredTool.from_function(
            func=lego_toolkits.callReShow,
            name='callReShow',
            description='Useful tool for calling LEGO AR system to repeat the current assembly step.'
        ),
        StructuredTool.from_function(
            func=lego_toolkits.callEnlarge,
            name='callEnlarge',
            description='Useful tool for calling LEGO AR system to enlarge or zoom out the current object.'
        ),
        StructuredTool.from_function(
            func=lego_toolkits.callShrink,
            name='callShrink',
            description='Useful tool for calling LEGO AR system to shrink or zoom in the current object.'
        ),
    ]
    agent_kwargs, memory = setup_memory()

    return initialize_agent(
        tools, 
        cfg.llm, 
        agent=AgentType.OPENAI_FUNCTIONS, 
        verbose=False, 
        agent_kwargs=agent_kwargs,
        memory=memory
    )