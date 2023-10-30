from dotenv import load_dotenv, find_dotenv
# load environment variables in .env file
load_dotenv(find_dotenv())

import langchain
from langchain.input import get_colored_text
from langchain.agents import AgentExecutor
from chain_setup import setup_agent, setup_agent_citl
from callbacks.agent_logger import AgentCallbackHandler

langchain.debug = True
from lcserve import serving

from typing import Any


def authorizer(token: str) -> Any:
    if not token == 'cwivox2023':  # Change this to add your own authorization logic
        raise Exception('Unauthorized')  # Raise an exception if the request is not authorized

    return token  # Return any user id or object


# Decorate the function with the @serving decorator for WebSocket communication
@serving(websocket=True)
async def citl(query: str, **kwargs) -> str:
    """
    Client in the loop
    :param query:
    :param kwargs:
    :return:
    """
    agent_executor: AgentExecutor = setup_agent_citl(**kwargs)
    try:
        # response = agent_executor.run(query)
        response = agent_executor.run(query, callbacks=[AgentCallbackHandler()])
        print(get_colored_text("Response: >>> ", "green"))
        print(get_colored_text(response, "green"))
    except Exception as e:
        print(get_colored_text(f"Failed to process {query}", "red"))
        print(get_colored_text(f"Error {e}", "red"))
    return response


# Decorate the function with the @serving decorator for HTTP communication
@serving
def ask(query: str, **kwargs) -> str:
    """
    This is the API for external systems (such as VR) ask DA their querys.
    :param query: transcript of the query from
    :return: a response object (see https://github.com/jina-ai/langchain-serve/blob/main/examples/rest/README.md)
    """
    agent_executor: AgentExecutor = setup_agent()
    try:
        response = agent_executor.run(query, callbacks=[AgentCallbackHandler()])
        print(get_colored_text("Response: >>> ", "green"))
        print(get_colored_text(response, "green"))
    except Exception as e:
        print(get_colored_text(f"Failed to process {query}", "red"))
        print(get_colored_text(f"Error {e}", "red"))
    return response