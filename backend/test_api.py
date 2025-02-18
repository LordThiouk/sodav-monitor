import asyncio
import websockets
import requests
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_connection(ws_url):
    """Test WebSocket connection"""
    try:
        logger.info(f"Testing WebSocket connection to {ws_url}...")
        async with websockets.connect(ws_url) as websocket:
            # Send test message
            test_message = {
                "type": "test",
                "message": "Hello from test client!",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(test_message))
            logger.info("✅ WebSocket message sent successfully")
            
            # Wait for response
            response = await websocket.recv()
            logger.info(f"Received WebSocket response: {response}")
            return True
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {str(e)}")
        return False

def test_api_endpoints(base_url):
    """Test REST API endpoints"""
    endpoints = {
        "health": "/api/health",
        "streams": "/api/streams",
        "stations": "/api/stations",
        "analytics": "/api/analytics/overview"
    }
    
    results = {}
    
    for name, endpoint in endpoints.items():
        try:
            logger.info(f"\nTesting {name} endpoint: {base_url}{endpoint}")
            response = requests.get(f"{base_url}{endpoint}")
            
            if response.status_code == 200:
                logger.info(f"✅ {name} endpoint test successful")
                logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
                results[name] = True
            else:
                logger.error(f"❌ {name} endpoint failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                results[name] = False
                
        except Exception as e:
            logger.error(f"❌ Error testing {name} endpoint: {str(e)}")
            results[name] = False
    
    return results

async def main():
    """Main test function"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get API URLs
        api_url = os.getenv("REACT_APP_API_URL", "http://localhost:3000")
        ws_url = os.getenv("REACT_APP_WS_URL", "ws://localhost:8000/ws")
        
        logger.info(f"Testing API connection to: {api_url}")
        logger.info(f"Testing WebSocket connection to: {ws_url}")
        
        # Test REST API endpoints
        logger.info("\n=== Testing REST API Endpoints ===")
        api_results = test_api_endpoints(api_url)
        
        # Test WebSocket connection
        logger.info("\n=== Testing WebSocket Connection ===")
        ws_result = await test_websocket_connection(ws_url.replace("wss:", "ws:"))
        
        # Summary
        logger.info("\n=== Test Summary ===")
        logger.info("REST API Tests:")
        for endpoint, success in api_results.items():
            logger.info(f"  {'✅' if success else '❌'} {endpoint}")
        logger.info(f"WebSocket Test: {'✅' if ws_result else '❌'}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main()) 