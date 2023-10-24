import langchain
from callbacks.agent_logger import AgentCallbackHandler
from langchain.input import get_colored_text
from dotenv import load_dotenv
from langchain.agents import AgentExecutor
load_dotenv()
from chain_setup import setup_agent

from prompt_toolkit import HTML, prompt, PromptSession
from prompt_toolkit.history import FileHistory

langchain.debug = True
from lcserve import serving


@serving
def ask(query: str) -> str:
    """
    This is the API for external systems (such as VR) ask DA their questions.
    :param query: transcript of the question from
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
    # ask('How many people live in canada as of 2023?')
    interactive()
    # pass
