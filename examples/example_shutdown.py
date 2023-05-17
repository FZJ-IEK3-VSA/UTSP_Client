"""
This example shows how to shutdown all UTSP workers
"""

import requests
from utspclient.client import shutdown


if __name__ == "__main__":
    URL = "http://localhost:443/api/v1/shutdown"
    API_KEY = ""
    shutdown(URL, API_KEY)
