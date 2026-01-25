import requests

    # Test the /end_reading route after starting the server
def test_end_reading():
    try:
        response = requests.post("http://127.0.0.1:8008/end_reading")
        print("Test /end_reading response:", response.json())
    except Exception as e:
        print("Error testing /end_reading:", e)
test_end_reading()