import langchain
from callbacks.agent_logger import AgentCallbackHandler
from langchain.input import get_colored_text
from dotenv import load_dotenv
from langchain.agents import AgentExecutor
load_dotenv()
from chain_setup import setup_agent, setup_agent_citl

from prompt_toolkit import HTML, prompt, PromptSession
from prompt_toolkit.history import FileHistory

langchain.debug = True
from lcserve import serving
from typing import Any

from dotenv import load_dotenv, find_dotenv
# load environment variables in .env file
load_dotenv(find_dotenv())


# Decorate the function with the @serving decorator for WebSocket communication
@serving(websocket=True)
async def citl(query: str, **kwargs) -> str:
    """
    Client in the loop
    :param query:
    :param kwargs:
    :return:
    """
    # auth_response = kwargs['auth_response']  # This will be 'userid'
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


@serving(websocket=True)
def hitl(query: str, **kwargs) -> str:
    from langchain.agents import initialize_agent, load_tools
    from langchain.callbacks.manager import CallbackManager
    from langchain.chat_models import ChatOpenAI
    from langchain.llms import OpenAI
    # Get the `streaming_handler` from `kwargs`. This is used to stream data to the client.
    streaming_handler = kwargs.get('streaming_handler')

    llm = ChatOpenAI(
        temperature=0.0,
        # verbose=True,
        streaming=True,  # Pass `streaming=True` to make sure the client receives the data.
        callback_manager=CallbackManager(
            [streaming_handler]
        ),  # Pass the callback handler
    )
    tools = load_tools(
        ["human"],
    )

    agent_chain = initialize_agent(
        tools,
        llm,
        agent="zero-shot-react-description",
        # verbose=True,
    )
    return agent_chain.run(query)


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


def interactive():
    agent_executor: AgentExecutor = setup_agent()

    session = PromptSession(history=FileHistory(".agent-history-file"))
    while True:
        query = session.prompt(
            HTML("<b>Type <u>Your query</u></b>  ('q' to exit): ")
        )
        if query.lower() == 'q':
            break
        if len(query) == 0:
            continue
        try:
            print(get_colored_text("Response: >>> ", "green"))
            print(get_colored_text(agent_executor.run(query, callbacks=[AgentCallbackHandler()]), "green"))
        except Exception as e:
            print(get_colored_text(f"Failed to process {query}", "red"))
            print(get_colored_text(f"Error {e}", "red"))


if __name__ == "__main__":
    # ask('Hi can you be my personal assistant to teach me how to assembly a LEGO car? ')
    # hitl('Hi can you be my personal assistant to teach me how to assembly a LEGO car? ')
    # interactive()
    pass
