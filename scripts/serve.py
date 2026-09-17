#!/usr/bin/env python3
"""Loopback-only static server. Never exposes source files or personal data."""
import functools,http.server,json,threading,urllib.request,webbrowser,os
from pathlib import Path
ROOT=Path(os.environ.get('LECTIO_DATA_ROOT',str(Path(__file__).resolve().parents[1])));PORT=8765
class Handler(http.server.SimpleHTTPRequestHandler):
 extensions_map={**http.server.SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript','.js':'text/javascript','.wasm':'application/wasm','.json':'application/json','.webmanifest':'application/manifest+json','.bin':'application/octet-stream'}
 def end_headers(self):
  self.send_header('Cache-Control','no-cache');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
 def log_message(self,*args):pass
url=f'http://localhost:{PORT}/'
try:server=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Handler,directory=str(ROOT/'dist')))
except OSError:
 try:
  m=json.load(urllib.request.urlopen(url+'manifest.webmanifest',timeout=2));assert m['short_name']=='Lectio'
  webbrowser.open(url);print('Lectio is already running at '+url);raise SystemExit(0)
 except Exception:raise SystemExit('Port 8765 is occupied by another app. Close it and reopen Lectio.')
threading.Timer(.6,lambda:webbrowser.open(url)).start();print('Lectio: '+url+'\nKeep this window open. Control-C stops the server. Internet is not required.',flush=True)
try:server.serve_forever()
except KeyboardInterrupt:server.server_close()
