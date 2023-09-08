"""
We implement APIs / interfaces to call the services and functions provided by AR system (Block Dream) for LEGO brick assembly task.
https://github.com/kukeya/2023-SWContest/tree/main/unity-script/*.cs
"""
import requests
import urllib.parse
import inspect


class ARSystemAPIWrapper:
    """
    all functions in AR system can be used by DA as external tools
    """
    def __init__(self):
        self.base_url = "http://your-ar-system-api-url.com"

    def callStartAssemble(self):
        return inspect.currentframe().f_code.co_name

    def callNextStep(self):
        return inspect.currentframe().f_code.co_name

    def callFrontStep(self):
        return inspect.currentframe().f_code.co_name

    def callExplode(self):
        return inspect.currentframe().f_code.co_name

    def callRecover(self):
        return inspect.currentframe().f_code.co_name

    def callFinishedVideo(self):
        return inspect.currentframe().f_code.co_name

    def callReShow(self):
        return inspect.currentframe().f_code.co_name

    def callEnlarge(self):
        return inspect.currentframe().f_code.co_name

    def callShrink(self):
        return inspect.currentframe().f_code.co_name


if __name__ == "__main__":
    ar_api = ARSystemAPIWrapper()
    print(ar_api.callStartAssemble())
    print(ar_api.callShrink())
    print(ar_api.callEnlarge())
    # Call other functions as needed.
