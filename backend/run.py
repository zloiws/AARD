"""Run script with proper environment loading"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load environment variables
from dotenv import load_dotenv

env_file = BASE_DIR / ".env"
load_dotenv(env_file, override=True)

# Set working directory to backend
os.chdir(Path(__file__).resolve().parent)

# Now import and run
if __name__ == "__main__":
    import uvicorn
    from app.core.config import get_settings
    
    settings = get_settings()
    
    # Import app directly instead of using string to avoid path issues
    from main import app
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=False,  # Disable reload to avoid path issues
    )

