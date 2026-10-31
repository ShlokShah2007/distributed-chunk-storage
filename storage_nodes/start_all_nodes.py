"""
Multi-Node Cluster Launcher
Author: Shlok Shah (@ShlokShah2007)
Purpose: Spawns 3 local storage nodes concurrently (ports 8001, 8002, 8003).
"""

import sys
import threading
from pathlib import Path
from http.server import HTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage_nodes.node_server import StorageNodeHandler
from core.config import STORAGE_API_KEY


class ThreadedNodeServer:
    def __init__(self, port: int, node_id: str, api_key: str):
        self.port = port
        self.node_id = node_id
        self.api_key = api_key
        self.server = None

    def start(self):
        storage_path = Path("storage_data") / self.node_id
        storage_path.mkdir(parents=True, exist_ok=True)

        class CustomHandler(StorageNodeHandler):
            server_node_id = self.node_id
            storage_dir = storage_path
            expected_api_key = self.api_key

        self.server = HTTPServer(("127.0.0.1", self.port), CustomHandler)
        print(f"  ✔ [{self.node_id}] Online at http://127.0.0.1:{self.port} (Authenticated)")
        self.server.serve_forever()


def start_cluster():
    print("=" * 65)
    print("  Starting 3-Node Storage Cluster with API Key Authentication")
    print(f"  Shared API Key: {STORAGE_API_KEY}")
    print("=" * 65)

    nodes = [
        (8001, "node-1"),
        (8002, "node-2"),
        (8003, "node-3"),
    ]

    threads = []
    for port, node_id in nodes:
        node = ThreadedNodeServer(port, node_id, STORAGE_API_KEY)
        t = threading.Thread(target=node.start, daemon=True)
        t.start()
        threads.append(t)

    print("\nAll 3 nodes are running! Press Ctrl+C to terminate cluster.\n")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nStopping cluster...")


if __name__ == "__main__":
    start_cluster()
