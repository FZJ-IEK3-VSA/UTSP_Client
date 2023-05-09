"""
This example shows how to shutdown all UTSP workers
"""

import requests


def shutdown_utsp():
    URL = "http://localhost:443/api/v1/shutdown"
    API_KEY = ""
    requests.post(URL, headers={"Authorization": API_KEY})


if __name__ == "__main__":
    shutdown_utsp()
