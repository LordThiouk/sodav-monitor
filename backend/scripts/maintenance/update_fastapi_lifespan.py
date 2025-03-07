#!/usr/bin/env python

"""
Script to update FastAPI on_event handlers to use the new lifespan system.
"""

import os
import re
from pathlib import Path

def update_main_py():
    """Update the main.py file to use the new lifespan system."""
    main_py_path = Path("backend/main.py")
    
    if not main_py_path.exists():
        print(f"Error: {main_py_path} does not exist")
        return False
    
    # Read the file
    content = main_py_path.read_text()
    
    # Add the import for asynccontextmanager if not present
    if "from contextlib import asynccontextmanager" not in content:
        content = re.sub(
            r"(from datetime import datetime)",
            r"from datetime import datetime\nfrom contextlib import asynccontextmanager",
            content
        )
    
    # Define the patterns to match
    startup_pattern = r"@app\.on_event\(\"startup\"\)\nasync def startup_event\(\):\n.*?try:.*?raise\n\n"
    shutdown_pattern = r"@app\.on_event\(\"shutdown\"\)\nasync def shutdown_event\(\):\n.*?logger\.error\(f\"Error during shutdown: {str\(e\)}\"\)\n\n"
    
    # Define the replacement lifespan function
    lifespan_function = """# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    \"\"\"Lifespan context manager for the application.\"\"\"
    # Startup
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")

        # Initialize Redis pool
        app.state.redis_pool = await init_redis_pool()
        logger.info("Redis pool initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

    yield  # Application runs here

    # Shutdown
    try:
        if hasattr(app.state, 'redis_pool'):
            await app.state.redis_pool.aclose()  # Using aclose() instead of close()
            logger.info("Redis pool closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

"""
    
    # Replace the on_event handlers with the lifespan function
    content = re.sub(startup_pattern, "", content, flags=re.DOTALL)
    content = re.sub(shutdown_pattern, "", content, flags=re.DOTALL)
    
    # Insert the lifespan function after the logger definition
    content = re.sub(
        r"(logger = logging\.getLogger\(__name__\))",
        r"\1\n\n" + lifespan_function,
        content
    )
    
    # Update the FastAPI app creation to include the lifespan parameter
    content = re.sub(
        r"app = FastAPI\(\n(.*?)\)",
        r"app = FastAPI(\n\1    lifespan=lifespan\n)",
        content,
        flags=re.DOTALL
    )
    
    # Write the updated content back to the file
    main_py_path.write_text(content)
    
    print(f"Updated {main_py_path}")
    return True

if __name__ == "__main__":
    update_main_py()



