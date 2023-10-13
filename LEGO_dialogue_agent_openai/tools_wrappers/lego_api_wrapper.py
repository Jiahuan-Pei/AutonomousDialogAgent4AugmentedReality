"""
We implement APIs / interfaces to call the services and functions provided by AR system (Block Dream) for LEGO brick assembly task.
https://github.com/kukeya/2023-SWContest/tree/main/unity-script/*.cs
"""
import requests
import urllib.parse
import inspect
import socket

"""
When to Choose Sockets:
- Use sockets when you need low-latency, real-time, or continuous communication.
- For scenarios like online games, chat applications, live streaming, or any application where rapid data transfer is crucial.
- When full-duplex communication is essential, and you want to maintain an open connection.

When to Choose RESTful API:
- Use RESTful APIs when you need a simple and web-friendly way to exchange data between applications.
- If you want to create an HTTP-based API that other services or clients can access.
- When real-time, low-latency communication is not a strict requirement.
"""

class LegoAPIWrapper:
    """
    all functions in AR system can be used by DA as external tools
    """
    def __init__(self):
        self.unity_host = "your_unity_host_ip"
        self.unity_port = 80

    def _call_unity_function_rest_api(self, function_name):
        url = f"{self.unity_host}:{self.unity_port}/{function_name}"
        response = requests.post(url)

        if response.status_code == 200:
            print(f"Unity function {function_name} successfully called.")
        else:
            print(f"Failed to call Unity function {function_name}.")

    def _call_unity_function(self, function_name):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.unity_host, self.unity_port))
            unity_function_name = function_name.encode("utf-8")
            unity_response = s.sendall(unity_function_name)
        return unity_response

    def callStartAssemble(self):
        return self._call_unity_function("StartAssemble")

    def callNextStep(self):
        return self._call_unity_function("NextStep")

    def callFrontStep(self):
        return self._call_unity_function("FrontStep")

    def callExplode(self):
        return self._call_unity_function("Explode")

    def callRecover(self):
        return self._call_unity_function("Recover")

    def callFinishedVideo(self):
        return self._call_unity_function("FinishedVideo")

    def callReShow(self):
        return self._call_unity_function("ReShow")

    def callEnlarge(self):
        return self._call_unity_function("Enlarge")

    def callShrink(self):
        return self._call_unity_function("Shrink")


if __name__ == "__main__":
    ar_api = LegoAPIWrapper()
    print(ar_api.callStartAssemble())
    print(ar_api.callShrink())
    print(ar_api.callEnlarge())
    # Call other functions as needed.
