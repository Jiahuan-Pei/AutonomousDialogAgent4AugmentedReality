import os
import json
import asyncio
import websockets
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from datetime import datetime
from fastapi import WebSocket


class LegoAPIWrapper:
    def __init__(self, loop=None):
        self.server_name = 'chatbot'
        self.sender_prefix = 'ToolUnity'
        self.secret_token = os.getenv('AUTHORIZER')
        self.description_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lego_function_description.json")
        self.url = f"ws://{os.getenv('HOST')}:{int(os.getenv('PORT'))+1}/{self.server_name}"    # !Important: Use plus one port to avoid issue
        # self.loop = loop if loop else asyncio.get_event_loop()
        self.loop = asyncio.get_event_loop()

        try:
            with open(self.description_file, "r") as file:
                self.descriptions = json.load(file)
        except FileNotFoundError:
            print(f'description file does not exist at {self.description_file}')
            self.descriptions = {}

        # Set class methods for LEGO functions
        for function_name, description in self.descriptions.items():
            class_method = self._create_class_method(function_name, description)
            setattr(self.__class__, function_name, class_method)

    async def _unity_function(self, function_name: str, **kwargs):
        try:
            async with websockets.connect(self.url, extra_headers=[("Authorization", f"Bearer {self.secret_token}")]) as websocket:
                request_message = f"{self.sender_prefix}: {function_name}"
                await websocket.send(request_message)
                print(f"{datetime.now()}\t {self.sender_prefix} sent >>>: {request_message}")

                response_message = await websocket.recv()
                if response_message.startswith('Unity:'):
                    sender, response = response_message.split(': ')
                    print(f"{datetime.now()}\t {self.sender_prefix} received Unity response <<<: {response_message}\n")
                    return response
                else:
                    print(f"{datetime.now()}\t {self.sender_prefix} received unexpected response: {response_message}\n")
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

    # def _create_class_method(self, function_name, description):
    #     async def async_method(**kwargs):
    #         f"""
    #         DA Python Function Doc:
    #         {function_name}:{description}
    #         Usage: result = LegoAPIWrapper.{function_name}
    #         """
    #         return await self._unity_function_wrapper(function_name, **kwargs)
    #
    #     def sync_method(self, **kwargs):
    #         result = self.loop.run_until_complete(async_method(**kwargs))
    #         # loop = asyncio.new_event_loop()
    #         # result = loop.run_until_complete(async_method(**kwargs))
    #         # loop.close()
    #         return result
    #
    #     sync_method.__doc__ = f"DA Python Function Doc:\n{function_name}:{description}\nUsage: result = LegoAPIWrapper.{function_name}"
    #     return sync_method

    def _create_class_method(self, function_name, description):
        async def async_method(self, **kwargs):
            f"""
            DA Python Function Doc:
            {function_name}:{description}
            Usage: result = LegoAPIWrapper.{function_name}
            """
            return await self._unity_function_wrapper(function_name, **kwargs)

        return async_method

    def __getattr__(self, function_name):
        if function_name in self.descriptions:
            return self._create_class_method(function_name, self.descriptions[function_name])
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{function_name}'")


def test_api():
    lego_api = LegoAPIWrapper()
    result1 = lego_api.StartAssemble()
    if result1 is not None:
        print(lego_api.StartAssemble.__doc__)


if __name__ == "__main__":
    test_api()
    # Can you start assemble?