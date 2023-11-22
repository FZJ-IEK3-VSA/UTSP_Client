"""
This example shows how to send a tar file containing the build context for a docker image
to the server, so that the server builds the new provider image.
This is done because the build context is usually significantly smaller than 
the built docker image file.
"""


import utspclient


if __name__ == "__main__":
    URL = "http://134.94.131.167:443/api/v1/buildimage"
    API_KEY = ""
    file_path = r"examples\HiSim.tar.gz"
    name = "hisim-1.0.0.0"
    utspclient.upload_provider_build_context(URL, API_KEY, file_path, name)
