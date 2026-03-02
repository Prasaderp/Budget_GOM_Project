import time
from collections import OrderedDict
from threading import Lock

class TTLCache:
    def __init__(self, maxsize=128, ttl=3600):
        self.cache = OrderedDict()
        self.timestamps = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
        self.lock = Lock()
    
    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return None
            if time.time() - self.timestamps[key] > self.ttl:
                del self.cache[key]
                del self.timestamps[key]
                return None
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def put(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache[key] = value
                self.timestamps[key] = time.time()
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.maxsize:
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    del self.timestamps[oldest_key]
                self.cache[key] = value
                self.timestamps[key] = time.time()
    
    def invalidate(self, key_prefix: str):
        with self.lock:
            keys = [k for k in self.cache if k.startswith(key_prefix)]
            for k in keys:
                del self.cache[k]
                del self.timestamps[k]

    def clear(self):
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
