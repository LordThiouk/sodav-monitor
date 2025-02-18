import asyncio
import websockets

async def test_websocket():
    try:
        async with websockets.connect('ws://localhost:8000/ws') as websocket:
            print("Connected to WebSocket")
            await websocket.send('test')
            print("Message sent")
            response = await websocket.recv()
            print(f"Received: {response}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 