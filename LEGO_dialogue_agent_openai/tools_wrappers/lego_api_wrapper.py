import os
import json
import asyncio
import websockets


class LegoAPIWrapper:
    def __init__(self):
        self.server_host = "localhost"
        self.server_port = 8080
        self.server_name = 'AR_LEGO'
        self.description_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lego_function_description.json")
        self.url = f"ws://{self.server_host}:{self.server_port}/{self.server_name}"

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

    async def _unity_function(self, function_name, **kwargs):
        async with websockets.connect(self.url) as websocket:
            print(f"DA Python: Send Function {function_name}")
            await websocket.send(function_name)
            response = await websocket.recv()
            print(f"DA Python: Get Response: {response}\n")
        return response

    @classmethod
    async def _unity_function_wrapper(cls, function_name, **kwargs):
        try:
            return await cls()._unity_function(function_name, **kwargs)
        except websockets.ConnectionClosedError:
            err_msg = f"DA Python: WebSocket connection to Unity Function {function_name} closed unexpectedly."
            print(err_msg)
            return None

    def _create_class_method(self, function_name, description):
        async def async_method(**kwargs):
            """
            Create a class method in the same way
            Example:
                usage:
                    result = LegoAPIWrapper.FunctionName()
            """
            return await self._unity_function_wrapper(function_name, **kwargs)

        def sync_method(self, **kwargs):
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(async_method(**kwargs))
            return result

        sync_method.__doc__ = f"DA Python Function Doc:\n{function_name}:{description}\nUsage: result = LegoAPIWrapper.{function_name}"
        return sync_method

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
