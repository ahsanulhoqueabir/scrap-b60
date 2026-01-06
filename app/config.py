"""
Configuration module for loading environment variables and app settings
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# Try .env first, then .env.local as fallback
env_path = Path(__file__).resolve().parent.parent / '.env'
env_local_path = Path(__file__).resolve().parent.parent / '.env.local'

if env_path.exists():
    load_dotenv(env_path)
elif env_local_path.exists():
    load_dotenv(env_local_path)


class Config:
    """Central configuration class"""
    
    # Database/API Configuration
    WEB_APP_URL = os.getenv("WEB_APP_URL", "")
    DIRECTUS_URL = os.getenv("DIRECTUS_URL", "")
    DIRECTUS_TOKEN = os.getenv("DIRECTUS_API_TOKEN", "")
    
    # Gemini API Configuration (supports multiple keys separated by comma)
    GEMINI_API_KEYS = [key.strip() for key in os.getenv("GEMINI_API_KEYS", "").split(",") if key.strip()]
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
    
    # Retry Configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))
    
    # Request Configuration
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # Scraper Configuration
    USER_AGENT = os.getenv(
        "USER_AGENT", 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
    )


# Create a global config instance
config = Config()
