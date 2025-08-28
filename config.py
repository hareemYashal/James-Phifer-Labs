import os
from dotenv import load_dotenv

# Load environment variables
try:
    load_dotenv()
except:
    pass

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# PDF Processing Configuration
MAX_PAGE_SIZE = 1024 * 1024  # 1MB max for API calls
SUPPORTED_IMAGE_FORMATS = ['JPEG', 'PNG', 'WEBP'] 