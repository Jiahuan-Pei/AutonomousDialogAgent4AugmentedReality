from fastapi import FastAPI, File
from langchain.agents import AgentExecutor
from starlette.responses import Response
import io
from chain_setup import setup_agent
from callbacks.agent_logger import AgentCallbackHandler
from langchain.input import get_colored_text

app = FastAPI(title="",
              description='''Obtain the response of an input via DA implemented in PyTorch.
                           Visit this URL at port 8501 for the streamlit interface.''',
              version="0.1.0",
              )


@app.websocket("/ask")
async def citl(query: str, **kwargs) -> str:
    agent_executor: AgentExecutor = setup_agent()
    if query.lower() == 'q':
        break
    if len(query) == 0:
        continue
    try:
        response = agent_executor.run(query, callbacks=[AgentCallbackHandler()])
        print(get_colored_text("Response: >>> ", "green"))
        print(get_colored_text(response, "green"))
    except Exception as e:
        print(get_colored_text(f"Failed to process {query}", "red"))
        print(get_colored_text(f"Error {e}", "red"))
    return response