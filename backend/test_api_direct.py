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

def test_api_endpoints(base_url):
    """Test API endpoints directly"""
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

async def test_websocket(ws_url):
    """Test WebSocket connection directly"""
    try:
        logger.info(f"\nTesting WebSocket connection to {ws_url}...")
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

async def main():
    """Main test function"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get environment variables
        api_port = os.getenv("API_PORT", "8000")
        host = os.getenv("HOST", "0.0.0.0")
        
        # Construct URLs
        base_url = f"http://localhost:{api_port}"
        ws_url = f"ws://localhost:{api_port}/ws"
        
        logger.info(f"Testing API at: {base_url}")
        logger.info(f"WebSocket URL: {ws_url}")
        
        # Test API endpoints
        logger.info("\n=== Testing API Endpoints ===")
        api_results = test_api_endpoints(base_url)
        
        # Test WebSocket
        logger.info("\n=== Testing WebSocket ===")
        ws_result = await test_websocket(ws_url)
        
        # Summary
        logger.info("\n=== Test Summary ===")
        logger.info("API Endpoints:")
        for endpoint, success in api_results.items():
            logger.info(f"  {'✅' if success else '❌'} {endpoint}")
        logger.info(f"WebSocket: {'✅' if ws_result else '❌'}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main()) 