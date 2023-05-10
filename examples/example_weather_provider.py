"""Requests TRY weather data"""

from utspclient.client import request_time_series_and_wait_for_delivery
from utspclient.datastructures import ResultDelivery, TimeSeriesRequest


def main():
    REQUEST_URL = "http://localhost:443/api/v1/profilerequest"
    API_KEY = ""

    weather_request = """{
        "reference_region": 1,
        "reference_condition": "a",
        "reference_projection": 2045,
        "resolution_in_min": 1
    }"""

    request = TimeSeriesRequest(weather_request, "weather_provider")
    result: ResultDelivery = request_time_series_and_wait_for_delivery(
        REQUEST_URL, request, API_KEY
    )
    data = result.data["weather_data.csv"].decode()

    # Print all results from the request
    print("Example weather provider request")
    print("Retrieved data: " + str(data.split("\n")[:10]))


if __name__ == "__main__":
    main()
