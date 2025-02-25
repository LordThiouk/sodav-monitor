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

def test_nginx_connection(base_url):
    """Test Nginx connection and static file serving"""
    try:
        logger.info(f"\nTesting Nginx connection to {base_url}...")
        
        # Test root path (should serve index.html)
        response = requests.get(base_url)
        if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
            logger.info("✅ Successfully accessed frontend index.html")
        else:
            logger.error(f"❌ Failed to access frontend. Status: {response.status_code}")
            return False
            
        # Test static file serving
        static_response = requests.get(f"{base_url}/static/")
        if static_response.status_code in [200, 301, 302, 404]:
            logger.info("✅ Static file serving configured")
        else:
            logger.error(f"❌ Static file serving failed. Status: {static_response.status_code}")
            return False
            
        # Test Nginx configuration
        headers_response = requests.options(f"{base_url}/api/health")
        cors_headers = headers_response.headers
        if "access-control-allow-origin" in cors_headers:
            logger.info("✅ CORS headers properly configured")
        else:
            logger.warning("⚠️ CORS headers might not be properly configured")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Nginx test failed: {str(e)}")
        return False

def test_api_through_nginx(base_url):
    """Test API endpoints through Nginx reverse proxy"""
    endpoints = {
        "health": "/api/health",
        "streams": "/api/streams",
        "stations": "/api/stations",
        "analytics": "/api/analytics/overview"
    }
    
    results = {}
    
    for name, endpoint in endpoints.items():
        try:
            logger.info(f"\nTesting {name} endpoint through Nginx: {base_url}{endpoint}")
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

async def test_websocket_through_nginx(ws_url):
    """Test WebSocket connection through Nginx"""
    try:
        logger.info(f"\nTesting WebSocket connection through Nginx to {ws_url}...")
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

def test_frontend_assets(base_url):
    """Test frontend static assets and routing"""
    try:
        logger.info("\nTesting frontend assets...")
        
        # Test index.html
        index_response = requests.get(base_url)
        if index_response.status_code == 200:
            logger.info("✅ Frontend index.html accessible")
        else:
            logger.error(f"❌ Frontend index.html not accessible. Status: {index_response.status_code}")
            return False
            
        # Test manifest.json
        manifest_response = requests.get(f"{base_url}/manifest.json")
        if manifest_response.status_code == 200:
            logger.info("✅ Frontend manifest.json accessible")
        else:
            logger.warning("⚠️ Frontend manifest.json not found")
            
        # Test static assets (CSS/JS)
        static_response = requests.get(f"{base_url}/static/")
        if static_response.status_code in [200, 301, 302, 404]:
            logger.info("✅ Static assets directory configured")
        else:
            logger.error(f"❌ Static assets not properly configured. Status: {static_response.status_code}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Frontend assets test failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get environment variables
        port = os.getenv("PORT", "3000")
        api_port = os.getenv("API_PORT", "8000")
        host = os.getenv("HOST", "0.0.0.0")
        
        # Construct URLs
        base_url = f"http://localhost:{port}"
        ws_url = f"ws://localhost:{port}/ws"
        
        logger.info(f"Testing application at: {base_url}")
        logger.info(f"API port: {api_port}")
        logger.info(f"WebSocket URL: {ws_url}")
        
        # Test Nginx
        logger.info("\n=== Testing Nginx Configuration ===")
        nginx_result = test_nginx_connection(base_url)
        
        # Test Frontend
        logger.info("\n=== Testing Frontend Assets ===")
        frontend_result = test_frontend_assets(base_url)
        
        # Test API through Nginx
        logger.info("\n=== Testing API through Nginx ===")
        api_results = test_api_through_nginx(base_url)
        
        # Test WebSocket through Nginx
        logger.info("\n=== Testing WebSocket through Nginx ===")
        ws_result = await test_websocket_through_nginx(ws_url)
        
        # Summary
        logger.info("\n=== Test Summary ===")
        logger.info(f"Nginx Configuration: {'✅' if nginx_result else '❌'}")
        logger.info(f"Frontend Assets: {'✅' if frontend_result else '❌'}")
        logger.info("API Endpoints:")
        for endpoint, success in api_results.items():
            logger.info(f"  {'✅' if success else '❌'} {endpoint}")
        logger.info(f"WebSocket: {'✅' if ws_result else '❌'}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main()) 