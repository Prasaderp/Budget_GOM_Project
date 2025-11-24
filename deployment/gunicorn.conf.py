import os
import multiprocessing

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count()))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
keepalive = 5
timeout = 30
graceful_timeout = 30
worker_tmp_dir = "/dev/shm"
