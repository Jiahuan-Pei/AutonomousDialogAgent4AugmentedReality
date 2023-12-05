import os
import json
import asyncio
import websockets
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from datetime import datetime
from fastapi import WebSocket
import concurrent.futures
from langchain.tools import tool


class LegoAPIWrapper:
    def __init__(self, websocket=None):
        self.server_name = 'chatbot'
        self.secret_token = os.getenv('AUTHORIZER')
        self.description_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lego_function_description.json")
        # self.url = f"ws://{os.getenv('HOST')}:{int(os.getenv('PORT'))}/{self.server_name}"    # !Important: Use plus one port to avoid issue
        self.url = f"ws://{os.getenv('HOST')}:{int(os.getenv('PORT'))}/{self.server_name}"    # !Important: Use plus one port to avoid issue for streamlit
        self.loop = asyncio.get_event_loop()
        self.sender_prefix = 'ToolUnity'

        try:
            with open(self.description_file, "r") as file:
                self.descriptions = json.load(file)
        except FileNotFoundError:
            print(f'description file does not exist at {self.description_file}')
            self.descriptions = {}

        # Set class methods for LEGO functions
        for function_name in self.descriptions:
            class_method = self._create_class_method(function_name)
            setattr(self.__class__, function_name, class_method)

    async def _unity_function(self, function_name: str, **kwargs):
        try:
            # Connect to the WebSocket
            websocket = await websockets.connect(self.url, extra_headers=[("Authorization", f"Bearer {self.secret_token}")])

            try:
                # Sending message
                request_message = f"{self.sender_prefix}: {function_name}"
                await websocket.send(request_message)
                print(f"{datetime.now()}\t {self.sender_prefix} sent >>>: {request_message}")

                # Receiving message with timeout
                try:
                    # Check if the WebSocket is still open before attempting to receive
                    if not websocket.open:
                        print(f"{datetime.now()}\t {self.sender_prefix} WebSocket connection is not open\n")
                        return "WebSocket connection is not open"
                    # Receiving message with timeout
                    response_message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    print(f"{datetime.now()}\t {self.sender_prefix} timed out while waiting for response\n")
                    return "Timeout error"

                if response_message.startswith('Unity:'):
                    sender, response = response_message.split(': ')
                    print(f"{datetime.now()}\t {self.sender_prefix} received Unity response <<<: {response_message}\n")
                    return response
                else:
                    print(f"{datetime.now()}\t {self.sender_prefix} received unexpected response: {response_message}\n")
            finally:
                pass
                # Close the WebSocket connection
                # if websocket.open:
                #     await websocket.close()

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"{datetime.now()}\t {self.sender_prefix} WebSocket connection closed unexpectedly: {str(e)}\n")
            return "WebSocket connection closed unexpectedly"

        except Exception as e:
            print(f"{datetime.now()}\t {self.sender_prefix} encountered an error: {str(e)}\n")
            return str(e)

    @classmethod
    async def _unity_function_wrapper(cls, function_name, **kwargs):
        try:
            return await cls()._unity_function(function_name, **kwargs)
        except websockets.ConnectionClosedError:
            err_msg = f"DA Python: WebSocket connection to Unity Function {function_name} closed unexpectedly."
            print(err_msg)
            return None

    def _create_class_method(self, function_name):
        async def async_method(**kwargs):
            f"""
            DA Python Function Doc:
            {function_name}:{self.descriptions[function_name]}
            Usage: result = LegoAPIWrapper.{function_name}
            """
            return await self._unity_function_wrapper(function_name, **kwargs)

        def sync_method(self, **kwargs):
            result = self.loop.run_until_complete(async_method(**kwargs))
            # loop = asyncio.new_event_loop()
            # result = loop.run_until_complete(async_method(**kwargs))
            # loop.close()
            return result

        sync_method.__doc__ = f"DA Python Function Doc:\n{function_name}:{self.descriptions[function_name]}\nUsage: result = LegoAPIWrapper.{function_name}"
        return sync_method

    # def _create_class_method(self, function_name, description):
    #     async def async_method(self, **kwargs):
    #         f"""
    #         DA Python Function Doc:
    #         {function_name}:{description}
    #         Usage: result = LegoAPIWrapper.{function_name}
    #         """
    #         return await self._unity_function_wrapper(function_name, **kwargs)
    #
    #     return async_method

    def __getattr__(self, function_name):
        if function_name in self.descriptions:
            return self._create_class_method(function_name)
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{function_name}'")


def test_api():
    lego_api = LegoAPIWrapper()
    result1 = lego_api.StartAssemble()
    if result1 is not None:
        print(lego_api.StartAssemble.__doc__)


if __name__ == "__main__":
    pass
    # test_api()
    # Can you start assemble?