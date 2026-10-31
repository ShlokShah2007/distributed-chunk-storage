"""
Storage Node HTTP Micro-Server
Author: Shlok Shah (@ShlokShah2007)
Purpose: Authenticated HTTP Server to store and serve encrypted chunk blobs.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Ensure parent directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.auth import AuthManager
from core.config import STORAGE_API_KEY


class StorageNodeHandler(BaseHTTPRequestHandler):
    """
    HTTP Request Handler enforcing API Key authentication on all chunk operations.
    """

    server_node_id = "node-1"
    storage_dir = Path("storage_data/node-1")
    expected_api_key = STORAGE_API_KEY

    def _send_json_response(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _is_authenticated(self) -> bool:
        incoming_key = self.headers.get(AuthManager.API_KEY_HEADER)
        return AuthManager.verify_api_key(incoming_key, self.expected_api_key)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.strip("/")

        # Health check does not require authentication
        if path == "health" or path == "":
            self._send_json_response(200, {
                "status": "healthy",
                "node_id": self.server_node_id,
                "auth_required": True
            })
            return

        # Authentication check for chunk downloads
        if not self._is_authenticated():
            self._send_json_response(401, {
                "status": "error",
                "message": f"Unauthorized. Missing or invalid '{AuthManager.API_KEY_HEADER}' header."
            })
            return

        # Format: /download/<chunk_name>
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "download":
            chunk_name = Path(parts[1]).name  # Sanitize
            chunk_file = self.storage_dir / chunk_name

            if not chunk_file.is_file():
                self._send_json_response(404, {
                    "status": "error",
                    "message": f"Chunk '{chunk_name}' not found on {self.server_node_id}."
                })
                return

            with open(chunk_file, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self._send_json_response(404, {"status": "error", "message": "Endpoint not found."})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.strip("/")

        # Authentication check
        if not self._is_authenticated():
            self._send_json_response(401, {
                "status": "error",
                "message": f"Unauthorized. Missing or invalid '{AuthManager.API_KEY_HEADER}' header."
            })
            return

        # Format: /upload/<chunk_name>
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "upload":
            chunk_name = Path(parts[1]).name  # Sanitize against path traversal
            content_length = int(self.headers.get("Content-Length", 0))

            if content_length == 0:
                self._send_json_response(400, {"status": "error", "message": "Empty chunk payload."})
                return

            chunk_bytes = self.rfile.read(content_length)

            self.storage_dir.mkdir(parents=True, exist_ok=True)
            chunk_file = self.storage_dir / chunk_name

            with open(chunk_file, "wb") as f:
                f.write(chunk_bytes)

            self._send_json_response(200, {
                "status": "success",
                "node_id": self.server_node_id,
                "chunk_name": chunk_name,
                "bytes_stored": len(chunk_bytes)
            })
            return

        self._send_json_response(404, {"status": "error", "message": "Endpoint not found."})

    def log_message(self, format, *args):
        # Mute default verbose stdout logs for cleaner demo output
        pass


def run_node_server(port: int = 8001, node_id: str = "node-1", api_key: str = STORAGE_API_KEY):
    storage_path = Path("storage_data") / node_id
    storage_path.mkdir(parents=True, exist_ok=True)

    StorageNodeHandler.server_node_id = node_id
    StorageNodeHandler.storage_dir = storage_path
    StorageNodeHandler.expected_api_key = api_key

    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, StorageNodeHandler)
    print(f"[{node_id}] Listening on http://127.0.0.1:{port} (API Key: {api_key[:8]}...)")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{node_id}] Shutting down...")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Storage Node Micro-Server")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on (default: 8001)")
    parser.add_argument("--id", type=str, default="node-1", help="Node identifier (default: node-1)")
    parser.add_argument("--key", type=str, default=STORAGE_API_KEY, help="Expected API Key")
    args = parser.parse_args()

    run_node_server(port=args.port, node_id=args.id, api_key=args.key)
