from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

EMBED_MODEL = "all-MiniLM-L6-v2"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

CHROMA_DIR = "./chroma_store"

TRANSFORMERS_CACHE = "/tmp/hf_cache"
ST_CACHE = "/tmp/st_cache"