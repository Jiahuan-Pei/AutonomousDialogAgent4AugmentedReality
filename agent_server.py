import os
from fastapi import FastAPI, WebSocket
import uvicorn
from dotenv import load_dotenv, find_dotenv
from langchain.agents import AgentExecutor
from chain_setup import setup_agent, setup_agent_streaming
from callbacks.agent_logger import AgentCallbackHandler
from langchain.input import get_colored_text
import asyncio
from datetime import datetime
import websockets
import callbacks
from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler

from tools_wrappers.lego_api_wrapper_da_request import LegoAPIWrapper

load_dotenv(find_dotenv())

sender_info_dict = {
    'Human': 'Human request as an input',
    'AI': 'AI agent response as an output',
    'ToolUnity': 'requested name of a Unity tool',
    'Unity': 'response of a called Unity tool'
}

app = FastAPI()
loop = asyncio.get_event_loop()

# Initialize client_connection as None
client_connection = None


async def authenticate_websocket(websocket: WebSocket):
    auth_header = websocket.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {os.getenv('AUTHORIZER')}":
        await websocket.close(code=4000, reason="Authentication failed")


async def generate_response(query: str, loop=None):
    # agent_executor = setup_agent_streaming()
    agent_executor = setup_agent(loop)
    try:
        # response = agent_executor.run(query, callbacks=[AgentCallbackHandler()])
        response = agent_executor.run(query, callbacks=[callbacks.StreamCallbackHandler()]) # the same streamlit agent
        # response = agent_executor.run(query, callbacks=[AsyncIteratorCallbackHandler()])
        # print(get_colored_text("Response: >>>", "green"))
        # print(get_colored_text(response, "green"))
    except Exception as e:
        print(get_colored_text(f"Failed to process {query}", "red"))
        print(get_colored_text(f"Error: {e}", "red"))
        response = str(e)
    return response


@app.websocket("/chatbot")
async def websocket_endpoint_chatbot(websocket: WebSocket):
    await authenticate_websocket(websocket)
    await websocket.accept()

    # Set the global client_connection variable to the WebSocket connection
    global client_connection
    client_connection = websocket

    prefix_sender = 'AI'

    # Create an event loop for the WebSocket connection
    loop = asyncio.get_event_loop()

    try:
        while True:
            message = await websocket.receive_text()
            print(get_colored_text(f"{datetime.now()}\t Server received <<<: {message}", "blue"))
            sender, info = message.split(': ')
            if sender == 'Human' or sender == 'Unity':
                response = await generate_response(info, loop)    # Call AI agent!
                if 'Tool: ' not in response:
                    message = f"{prefix_sender}: {response}"
                    await websocket.send_text(message)
                    print(get_colored_text(f"{datetime.now()}\t Server ({prefix_sender}) sent >>>: {message}", "green"))
                else:
                    await websocket.send_text(message)
                    print(get_colored_text(f"{datetime.now()}\t Server ({prefix_sender}) sent >>>: {message}", "red"))
            else:
                pass
    except websockets.exceptions.ConnectionClosedOK:
        # Handle disconnections
        client_connection = None


if __name__ == '__main__':
    uvicorn.run(app, host=os.getenv('HOST'), port=int(os.getenv('PORT')))
