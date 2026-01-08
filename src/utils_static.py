import os
import hashlib
import mimetypes
from typing import Dict, Optional
from datetime import datetime, timedelta
import gzip
try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False
from fastapi import Response
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
import aiofiles
import asyncio

class OptimizedStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache: Dict[str, bytes] = {}
        self.etags: Dict[str, str] = {}
        
    async def get_response(self, path: str, scope) -> Response:
        full_path = os.path.join(self.directory, path)
        
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            return await super().get_response(path, scope)
        
        file_stat = os.stat(full_path)
        etag = self.get_etag(full_path, file_stat)
        
        headers = scope.get("headers", [])
        if_none_match = None
        accept_encoding = ""
        
        for header_name, header_value in headers:
            if header_name == b"if-none-match":
                if_none_match = header_value.decode()
            elif header_name == b"accept-encoding":
                accept_encoding = header_value.decode()
        
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})
        
        content = await self.get_cached_content(full_path)
        
        content_type, _ = mimetypes.guess_type(full_path)
        if not content_type:
            content_type = "application/octet-stream"
        
        response_headers = {
            "ETag": etag,
            "Cache-Control": self.get_cache_control(path),
            "Last-Modified": datetime.utcfromtimestamp(file_stat.st_mtime).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Vary": "Accept-Encoding",
        }
        
        if HAS_BROTLI and "br" in accept_encoding and len(content) > 1000:
            compressed = brotli.compress(content, quality=4)
            if len(compressed) < len(content) * 0.9:
                response_headers["Content-Encoding"] = "br"
                content = compressed
        elif "gzip" in accept_encoding and len(content) > 1000:
            compressed = gzip.compress(content, compresslevel=6)
            if len(compressed) < len(content) * 0.9:
                response_headers["Content-Encoding"] = "gzip"
                content = compressed
        
        return Response(
            content=content,
            status_code=200,
            headers=response_headers,
            media_type=content_type
        )
    
    def get_etag(self, path: str, stat_result) -> str:
        if path in self.etags:
            return self.etags[path]
        
        etag_data = f"{path}-{stat_result.st_mtime}-{stat_result.st_size}"
        etag = f'"{hashlib.md5(etag_data.encode()).hexdigest()}"'
        self.etags[path] = etag
        return etag
    
    async def get_cached_content(self, path: str) -> bytes:
        if path in self.cache:
            return self.cache[path]
        
        async with aiofiles.open(path, 'rb') as f:
            content = await f.read()
        
        if len(content) < 1024 * 1024:
            self.cache[path] = content
        
        return content
    
    def get_cache_control(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        
        if ext in ['.js', '.css']:
            return "public, max-age=31536000, immutable"
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico']:
            return "public, max-age=2592000"
        elif ext in ['.woff', '.woff2', '.ttf', '.eot']:
            return "public, max-age=31536000"
        else:
            return "public, max-age=3600"

def minify_css(css: str) -> str:
    import re
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    css = re.sub(r'\s+', ' ', css)
    css = re.sub(r':\s+', ':', css)
    css = re.sub(r';\s+', ';', css)
    css = re.sub(r'\s*{\s*', '{', css)
    css = re.sub(r'\s*}\s*', '}', css)
    css = re.sub(r'\s*,\s*', ',', css)
    return css.strip()

def minify_js(js: str) -> str:
    import re
    js = re.sub(r'//.*?$', '', js, flags=re.MULTILINE)
    js = re.sub(r'/\*.*?\*/', '', js, flags=re.DOTALL)
    js = re.sub(r'\s+', ' ', js)
    js = re.sub(r'\s*([{}();,:])\s*', r'\1', js)
    return js.strip()

async def optimize_static_files(static_dir: str):
    for root, dirs, files in os.walk(static_dir):
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            
            if ext == '.css':
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                minified = minify_css(content)
                if len(minified) < len(content):
                    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                        await f.write(minified)
                    print(f"Optimized CSS: {file_path}")
            
            elif ext == '.js':
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                minified = minify_js(content)
                if len(minified) < len(content):
                    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                        await f.write(minified)
                    print(f"Optimized JS: {file_path}")
