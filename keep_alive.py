# keep_alive.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"I'm alive!")

def run_keep_alive_server():
    server = HTTPServer(('0.0.0.0', 8080), KeepAliveHandler)
    print("🧬 Keep-alive HTTP server running on port 8080")
    server.serve_forever()

def keep_alive():
    thread = threading.Thread(target=run_keep_alive_server)
    thread.daemon = True
    thread.start()
