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
import json

from tools_wrappers.lego_api_wrapper_da_request import LegoAPIWrapper

load_dotenv(find_dotenv())

sender_info_dict = {
    'Human': 'Human request as an input',
    'AI': 'AI agent response as an output',
    'ToolUnity': 'requested name of a Unity tool',
    'Unity': 'response of a called Unity tool'
}

app = FastAPI()

# Initialize client_connection as None
client_connection = None


async def authenticate_websocket(websocket: WebSocket):
    auth_header = websocket.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {os.getenv('AUTHORIZER')}":
        await websocket.close(code=4000, reason="Authentication failed")


async def generate_response(query: str, agent_executor: AgentExecutor) -> str:
    try:
        response = agent_executor.run(query, callbacks=[callbacks.StreamCallbackHandler()])
        print(get_colored_text("Response: >>>", "green"))
        print(get_colored_text(response, "green"))
    except Exception as e:
        print(get_colored_text(f"Failed to process {query}", "red"))
        print(get_colored_text(f"Error: {e}", "red"))
        response = str(e)
    return response


@app.websocket("/chatbot")
async def websocket_endpoint_chatbot(websocket: WebSocket):
    await authenticate_websocket(websocket)
    await websocket.accept()

    api = LegoAPIWrapper()
    api.add_websocket(websocket)

    agent_executor: AgentExecutor = setup_agent()

    try:
        while True:
            message = await websocket.receive_text()
            print(get_colored_text(f"{datetime.now()}\t Server received <<<: {message}", "blue"))

            sender, info = message.split(":", 1)
            sender = sender.strip()
            if sender == 'Human' or sender == 'Unity':
                prefix_sender = 'AI'
                response = await generate_response(info, agent_executor)    # Call AI agent!
                await websocket.send_text(response)
                print(get_colored_text(f"{datetime.now()}\t Server ({prefix_sender}) sent >>>: {message}", "red"))
            elif sender == 'ToolUnity':
                function_name, params = info.split(' ')
                params = json.loads(params.strip()) if params else None
                if hasattr(api, function_name):
                    result = await getattr(api, function_name)(websocket=websocket, **params)
                    print(get_colored_text(f"{datetime.now()}\t Server ({sender}) sent >>>: {result}", "orange"))
                    if result is not None:
                        await websocket.send_text(result)

    except websockets.exceptions.ConnectionClosedOK:
        api.websockets.remove(websocket)

    # agent_executor = setup_agent(websocket)
    #
    # prefix_sender = 'AI'
    #
    # try:
    #     while True:
    #         message = await websocket.receive_text()
    #         print(get_colored_text(f"{datetime.now()}\t Server received <<<: {message}", "blue"))
    #         response = await generate_response(message, agent_executor)
    #         await websocket.send_text(response)
    #         # sender, info = message.split(': ')
    #         # if sender == 'Human' or sender == 'Unity':
    #         #     response = await generate_response(info)    # Call AI agent!
    #         #     await websocket.send_text(response)
    #         #     print(get_colored_text(f"{datetime.now()}\t Server ({prefix_sender}) sent >>>: {message}", "red"))
    #         #     # if 'Tool: ' not in response:
    #         #     #     message = f"{prefix_sender}: {response}"
    #         #     #     await websocket.send_text(message)
    #         #     #     print(get_colored_text(f"{datetime.now()}\t Server ({prefix_sender}) sent >>>: {message}", "green"))
    #         #     # else:
    #         #     #     await websocket.send_text(message)
    #         #     #     print(get_colored_text(f"{datetime.now()}\t Server ({prefix_sender}) sent >>>: {message}", "red"))
    #         # else:
    #         #     pass
    # except websockets.exceptions.ConnectionClosedOK:
    #     # Handle disconnections
    #     client_connection = None


if __name__ == '__main__':
    uvicorn.run(app, host=os.getenv('HOST'), port=int(os.getenv('PORT')))
