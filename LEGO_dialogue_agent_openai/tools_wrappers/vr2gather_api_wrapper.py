"""
We implement APIs / interfaces to call the services and functions provided by AR system (Block Dream) for LEGO brick assembly task.
https://github.com/kukeya/2023-SWContest/tree/main/unity-script/*.cs
"""
import requests
import urllib.parse
import inspect


class VR2GatherAPIWrapper:
    """
    all functions in VR2Gather can be used by DA as external tools https://github.com/Jiahuan-Pei/VR2Gather/blob/master/Assets/Pilots/SoloPlayground/TestInteractable.cs
    """
    def __init__(self):
        self.base_url = "http://your-ar-system-api-url.com"

    def callOnActivate(self):
        return inspect.currentframe().f_code.co_name

    def callOnDeactivate(self):
        return inspect.currentframe().f_code.co_name

    def callOnHoverEnter(self):
        return inspect.currentframe().f_code.co_name

    def callOnHoverExit(self):
        return inspect.currentframe().f_code.co_name

    def callOnSelectEnter(self):
        return inspect.currentframe().f_code.co_name

    def callOnSelectExit(self):
        return inspect.currentframe().f_code.co_name

    def callOnTeleporting(self):
        return inspect.currentframe().f_code.co_name


if __name__ == "__main__":
    ar_api = VR2GatherAPIWrapper()
    print(ar_api.callStartAssemble())
    print(ar_api.callShrink())
    print(ar_api.callEnlarge())
    # Call other functions as needed.
