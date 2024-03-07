"""
This example shows how to shutdown all UTSP workers
"""

from utspclient.client import shutdown


if __name__ == "__main__":
    URL = "localhost:443"
    API_KEY = ""
    shutdown(URL, API_KEY)
