import os
import hashlib
import mimetypes
from typing import Dict, Optional
from datetime import datetime
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
    _BINARY_EXTENSIONS = frozenset({
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.ico',
        '.woff', '.woff2', '.ttf', '.eot', '.mp4', '.mp3', '.zip',
    })
    _CACHE_CONTROL_MAP = {
        '.js': 'public, max-age=31536000, immutable',
        '.css': 'public, max-age=31536000, immutable',
        '.woff': 'public, max-age=31536000, immutable',
        '.woff2': 'public, max-age=31536000, immutable',
        '.ttf': 'public, max-age=31536000, immutable',
        '.eot': 'public, max-age=31536000, immutable',
        '.jpg': 'public, max-age=2592000',
        '.jpeg': 'public, max-age=2592000',
        '.png': 'public, max-age=2592000',
        '.gif': 'public, max-age=2592000',
        '.svg': 'public, max-age=2592000',
        '.webp': 'public, max-age=2592000',
        '.ico': 'public, max-age=2592000',
        '.pdf': 'public, max-age=86400',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._text_cache: Dict[str, bytes] = {}
        self._etags: Dict[str, str] = {}

    async def get_response(self, path: str, scope) -> Response:
        full_path = os.path.join(self.directory, path)

        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            return await super().get_response(path, scope)

        ext = os.path.splitext(path)[1].lower()

        if ext in self._BINARY_EXTENSIONS:
            return FileResponse(
                full_path,
                headers={'Cache-Control': self._CACHE_CONTROL_MAP.get(ext, 'public, max-age=3600')},
            )

        file_stat = os.stat(full_path)
        etag = self._compute_etag(full_path, file_stat)

        if_none_match = self._extract_header(scope, b'if-none-match')
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={'ETag': etag})

        accept_encoding = self._extract_header(scope, b'accept-encoding') or ''
        content = await self._read_text_cached(full_path)

        content_type, _ = mimetypes.guess_type(full_path)
        content_type = content_type or 'application/octet-stream'

        response_headers = {
            'ETag': etag,
            'Cache-Control': self._CACHE_CONTROL_MAP.get(ext, 'public, max-age=3600'),
            'Last-Modified': datetime.utcfromtimestamp(file_stat.st_mtime).strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Vary': 'Accept-Encoding',
        }

        if HAS_BROTLI and 'br' in accept_encoding and len(content) > 1000:
            compressed = brotli.compress(content, quality=4)
            if len(compressed) < len(content) * 0.9:
                response_headers['Content-Encoding'] = 'br'
                return Response(content=compressed, status_code=200, headers=response_headers, media_type=content_type)

        if 'gzip' in accept_encoding and len(content) > 1000:
            compressed = gzip.compress(content, compresslevel=6)
            if len(compressed) < len(content) * 0.9:
                response_headers['Content-Encoding'] = 'gzip'
                return Response(content=compressed, status_code=200, headers=response_headers, media_type=content_type)

        return Response(content=content, status_code=200, headers=response_headers, media_type=content_type)

    @staticmethod
    def _extract_header(scope, name: bytes) -> Optional[str]:
        for k, v in scope.get('headers', []):
            if k == name:
                return v.decode()
        return None

    def _compute_etag(self, path: str, stat_result) -> str:
        if path not in self._etags:
            raw = f'{path}-{stat_result.st_mtime}-{stat_result.st_size}'
            self._etags[path] = f'"{hashlib.md5(raw.encode()).hexdigest()}"'
        return self._etags[path]

    async def _read_text_cached(self, path: str) -> bytes:
        if path not in self._text_cache:
            async with aiofiles.open(path, 'rb') as f:
                content = await f.read()
            if len(content) < 512 * 1024:
                self._text_cache[path] = content
            return content
        return self._text_cache[path]

    def get_cache_control(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        return self._CACHE_CONTROL_MAP.get(ext, 'public, max-age=3600')

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
