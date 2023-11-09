import websockets
import asyncio
import os
from dotenv import load_dotenv, find_dotenv
from langchain.input import get_colored_text
from datetime import datetime
import random

load_dotenv(find_dotenv())

import json


unity_callable_functions = {
    "StartAssemble": "Useful tool for initiating the assembly process.",
    "NextStep": "Useful tool for moving to the next assembly step.",
    "FrontStep": "Useful tool for going back to the previous assembly step.",
    "Explode": "Useful tool for triggering an explosion for detailed viewing.",
    "Recover": "Useful tool for restoring the initial state of AR objects after explosion.",
    "FinishedVideo": "Useful tool for ending the assembly process and showing a video of the assembled LEGO bricks.",
    "ReShow": "Useful tool for repeating the current assembly step.",
    "Enlarge": "Useful tool for enlarging or zooming out the current object.",
    "Shrink": "Useful tool for shrinking or zooming in the current object.",
    # Add more functions as needed
}

sender_info_dict = {
    'Human': 'Human request as an input',
    'AI': 'AI agent response as an output',
    'ToolUnity': 'requested name of a Unity tool',
    'Unity': 'response of a called Unity tool'
}


async def unity_simulation_response(function_name, **params):
    """
    This simulates the AR application is always running to reply DA's request when receiving its message.
    """
    sender_prefix = 'Unity'
    uri = f"ws://{os.getenv('HOST')}:{int(os.getenv('PORT'))+1}/chatbot"  # !Important: Use plus one port to avoid issue
    extra_headers = [("Authorization", f"Bearer {os.getenv('AUTHORIZER')}")]
    async with websockets.connect(uri, extra_headers=extra_headers) as websocket:
        if function_name in unity_callable_functions:
            responses = [
                f"Great, function {function_name} called successfully.",
                f"Sorry, function {function_name} called unsuccessfully.",
                f"Sorry, you have to wait, I am trying to call function {function_name}."
            ]
            weights = [0.7, 0.2, 0.1]
            unity_response = random.choices(responses, weights=weights)[0]
        else:
            unity_response = f"Sorry, function {function_name} is not implemented yet."
        message = f"{sender_prefix}: {unity_response}"
        await websocket.send(message)
        print(get_colored_text(f"{datetime.now()}\t {sender_prefix} sent >>> :\t{message}", "orange"))


# Function to run the client in the main thread
async def client_main():
    uri = f"ws://{os.getenv('HOST')}:{os.getenv('PORT')}/chatbot"
    extra_headers = [("Authorization", f"Bearer {os.getenv('AUTHORIZER')}")]
    # print(uri)
    # print(extra_headers)
    async with websockets.connect(uri, extra_headers=extra_headers) as websocket:
        print("WebSocket connection established.")
        while True:
            user_input = input("Human: ")
            await websocket.send(f"Human: {user_input}")

            message = await websocket.recv()
            print(get_colored_text(f"Unity Client: {datetime.now()}\t received:\t{message}", "pink"))

            parts = message.strip('\n').split(':')
            sender = parts[0]
            if sender == 'ToolUnity':
                sender_prefix = 'Unity'
                function_name, params = parts[1].split(' ')
                params = json.loads(params.strip()) if params else None
                unity_response = await unity_simulation_response(function_name, **params)
                message = f"{sender_prefix}: {unity_response}"
                await websocket.send(message)
                print(get_colored_text(f"{datetime.now()}\t {sender_prefix} sent >>> :\t{message}", "orange"))
            elif message.startswith('AI'):
                print(get_colored_text(f"{datetime.now()}\t Unity received final answer and show the response to human *** \n:\t{message}", "green"))
            else:
                pass


if __name__ == "__main__":
    # Can you start assemble?
    asyncio.get_event_loop().run_until_complete(client_main())


