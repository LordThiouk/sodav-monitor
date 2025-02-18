import requests
import json

BASE_URL = "http://localhost:3000/api"

def test_health():
    response = requests.get(f"{BASE_URL}/health")
    print("Health check:", response.status_code, response.text)

def test_stations():
    response = requests.get(f"{BASE_URL}/stations")
    print("Stations:", response.status_code, response.text)

def test_analytics():
    response = requests.get(f"{BASE_URL}/analytics/overview")
    print("Analytics:", response.status_code, response.text)

def test_websocket():
    import websockets
    import asyncio
    
    async def test_ws():
        try:
            async with websockets.connect("ws://localhost:3000/ws") as websocket:
                await websocket.send("test")
                response = await websocket.recv()
                print("WebSocket test:", response)
        except Exception as e:
            print("WebSocket error:", str(e))
    
    asyncio.get_event_loop().run_until_complete(test_ws())

if __name__ == "__main__":
    print("\nTesting API endpoints...")
    test_health()
    test_stations()
    test_analytics()
    test_websocket() 