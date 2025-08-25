
import os
from pathlib import Path
from dotenv import load_dotenv

def env_loader():
    BASE_DIR = Path(__file__).resolve().parents[2]   # backend/app
    return BASE_DIR
