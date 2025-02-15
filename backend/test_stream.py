import asyncio
import aiohttp
import logging
import soundfile as sf
import io
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_radio_stream(url: str):
    """Test if we can connect to and read audio from the radio stream"""
    try:
        async with aiohttp.ClientSession() as session:
            logger.info("Connecting to stream...")
            async with session.get(url) as response:
                if response.status == 200:
                    logger.info("✅ Successfully connected to stream")
                    logger.info(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
                    
                    # Try to read some data
                    chunk_size = 8192  # 8KB chunks
                    chunks_to_read = 5  # Read 5 chunks (40KB total)
                    chunks = []
                    
                    logger.info("Reading audio data...")
                    for _ in range(chunks_to_read):
                        chunk = await response.content.read(chunk_size)
                        if not chunk:
                            break
                        chunks.append(chunk)
                    
                    if chunks:
                        total_bytes = sum(len(chunk) for chunk in chunks)
                        logger.info(f"✅ Successfully read {total_bytes} bytes of audio data")
                        
                        # Try to analyze the first few bytes
                        first_bytes = chunks[0][:20]
                        logger.info(f"First few bytes (hex): {first_bytes.hex()}")
                    else:
                        logger.error("❌ No data received from stream")
                else:
                    logger.error(f"❌ Failed to connect to stream: Status {response.status}")
                    
    except Exception as e:
        logger.error(f"❌ Error testing stream: {str(e)}")

if __name__ == "__main__":
    url = "https://stream-166.zeno.fm/rq40edfn3reuv?zt=eyJhbGciOiJIUzI1NiJ9.eyJzdHJlYW0iOiJycTQwZWRmbjNyZXV2IiwiaG9zdCI6InN0cmVhbS0xNjYuemVuby5mbSIsInJ0dGwiOjUsImp0aSI6IjJSX2w4VXREVDktQ3Q5azR3dTZaT1EiLCJpYXQiOjE3Mzg3Njk5NzksImV4cCI6MTczODc3MDAzOX0.uQZSMMJSLBQBjL-mInuEBjft6V1md2FUX7skSuUTDmU"
    asyncio.run(test_radio_stream(url))
