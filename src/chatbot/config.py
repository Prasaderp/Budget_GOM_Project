import os
import sys
from threading import Lock, RLock, Semaphore
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# NeonDB Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable not found.")
    sys.exit(1)

if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not found.")
    sys.exit(1)

# Parse DATABASE_URL for individual connection parameters
from urllib.parse import urlparse, parse_qs

parsed_url = urlparse(DATABASE_URL)
DB_USER = parsed_url.username
DB_PASSWORD = parsed_url.password or ""
DB_HOST = parsed_url.hostname
DB_PORT = str(parsed_url.port) if parsed_url.port else "5432"
DB_NAME = parsed_url.path.lstrip('/')

DB_SSLMODE = os.getenv(
    "DB_SSLMODE",
    "require" if DB_HOST not in ("localhost", "127.0.0.1") else "disable",
)

if not all([DB_USER, DB_HOST, DB_NAME]):
    print("Error: DATABASE_URL is missing required components (user, host, or database name).")
    sys.exit(1)

print("Configuration loaded:")
print(f"  DB User: {DB_USER}")
print(f"  DB Password: {'Set (Hidden)' if DB_PASSWORD else 'Not Set'}")
print(f"  DB Host: {DB_HOST}")
print(f"  DB Port: {DB_PORT}")
print(f"  DB Name: {DB_NAME}")

# Convert DATABASE_URL to psycopg2 format for chatbot
DATABASE_URI = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://") if DATABASE_URL.startswith("postgresql://") else DATABASE_URL

MAX_WORKERS = min(100, max(20, os.cpu_count() * 4))
MAX_CACHE_SIZE = 1000
MAX_QUERY_CACHE_SIZE = 500
MAX_DEDUP_CACHE_SIZE = 200
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 60

llm = None
connection_pool = None
schema_cache = OrderedDict()
query_cache = OrderedDict()
request_dedup_cache = OrderedDict()
cache_lock = RLock()
dedup_lock = RLock()
rate_limiter = Semaphore(50)
db_circuit_breaker = {'failures': 0, 'last_failure': None, 'state': 'closed'}
circuit_breaker_lock = Lock()

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="chatbot")
db_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="db_pool")

dedup_requests = {}
