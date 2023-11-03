import asyncio
import websockets
import random
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


async def unity_simulation_response(websocket):
    """
    This simulates the AR application is always running to reply DA's request when receiving its message.
    """
    send_prefix = 'Unity'
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

    async for message in websocket:
        sender, info = message.split(': ')
        if sender == 'ToolUnity':
            if info in unity_callable_functions:
                responses = [
                    f"Great, function {info} called successfully.",
                    f"Sorry, function {info} called unsuccessfully.",
                    f"Sorry, you have to wait, I am trying to call function {info}."
                ]
                weights = [0.7, 0.2, 0.1]  # Ensure the number of weights matches the number of responses
                response = random.choices(responses, weights=weights)[0]
            else:
                response = f" Sorry, function {info} is not implemented yet."
            message = f"{send_prefix}: {response}"
            await websocket.send(message)
            print(message)

if __name__ == "__main__":
    # Start the WebSocket server
    # # Can you start assemble?
    start_server = websockets.serve(unity_simulation_response, os.getenv('HOST'), int(os.getenv('PORT'))+1)  # the endpoint should be the same with LegoAPIWrapper
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
