import requests
import json
from datetime import datetime
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_feature_value(value):
    """Format feature values for display"""
    if isinstance(value, float):
        if value < 0.01:
            return f"{value:.2e}"
        return f"{value:.2f}"
    return str(value)

def print_separator(char="-", length=60):
    print(char * length)

def test_detection():
    try:
        response = requests.post('http://localhost:8000/api/channels/detect-music')
        print("Status Code:", response.status_code)
        print("Response:", json.dumps(response.json(), indent=2))
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    test_detection() 