# load environment variables in .env file
from dotenv import load_dotenv, find_dotenv
import langchain
from langchain.input import get_colored_text
from langchain.agents import AgentExecutor
from prompt_toolkit import HTML, PromptSession
from prompt_toolkit.history import FileHistory

from callbacks.agent_logger import AgentCallbackHandler
from chain_setup import setup_agent

load_dotenv(find_dotenv())
langchain.debug = True


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
    interactive()
    pass
