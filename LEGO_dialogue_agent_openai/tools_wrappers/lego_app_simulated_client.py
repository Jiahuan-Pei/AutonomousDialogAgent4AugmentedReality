import asyncio
import websockets
import random


async def unity_simulation(websocket, path):
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
        if message in unity_callable_functions:
            responses = [
                f"LEGO AR Unity: Great, function {message} called successfully.",
                f"LEGO AR Unity: Sorry, function {message} called unsuccessfully.",
                f"LEGO AR Unity: Sorry, you have to wait, I am trying to call function {message}."
            ]
            weights = [0.7, 0.2, 0.1]  # Ensure the number of weights matches the number of responses
            response = random.choices(responses, weights=weights)[0]
        else:
            response = f"LEGO AR Unity: Sorry, function {message} is not implemented yet."
        await websocket.send(response)
        print(response)

if __name__ == "__main__":
    start_server = websockets.serve(unity_simulation, "localhost", 8080)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

