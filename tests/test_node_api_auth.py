"""
Unit Tests for Storage Node API & Key Authentication
Author: Shlok Shah (@ShlokShah2007)
"""

import os
# Prevent requests from routing localhost connections through proxy
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

import shutil
import unittest
import threading
import tempfile
import requests
from pathlib import Path
from http.server import HTTPServer

from core.auth import AuthManager
from storage_nodes.node_server import StorageNodeHandler


class TestNodeAPIAndAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(tempfile.mkdtemp())
        cls.test_api_key = "test_key_abc123xyz"
        cls.port = 8899
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        # Use session with trust_env=False to bypass system proxies
        cls.session = requests.Session()
        cls.session.trust_env = False

        class TestHandler(StorageNodeHandler):
            server_node_id = "test-node"
            storage_dir = cls.test_dir
            expected_api_key = cls.test_api_key

        cls.httpd = HTTPServer(("127.0.0.1", cls.port), TestHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_auth_manager_logic(self):
        """Test API key generation and constant-time validation."""
        generated_key = AuthManager.generate_api_key()
        self.assertTrue(generated_key.startswith("chunk_sec_key_"))
        self.assertEqual(len(generated_key), 46)

        self.assertTrue(AuthManager.verify_api_key("my_key", "my_key"))
        self.assertFalse(AuthManager.verify_api_key("wrong_key", "my_key"))
        self.assertFalse(AuthManager.verify_api_key("", "my_key"))

    def test_health_check_unauthenticated(self):
        """Health check should return 200 without requiring API key."""
        res = self.session.get(f"{self.base_url}/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["node_id"], "test-node")

    def test_upload_without_api_key_fails(self):
        """Uploading without X-API-Key must return 401 Unauthorized."""
        payload = b"encrypted chunk blob without key"
        res = self.session.post(f"{self.base_url}/upload/chunk_0.enc", data=payload)
        self.assertEqual(res.status_code, 401)
        self.assertIn("Unauthorized", res.json()["message"])

    def test_upload_with_invalid_api_key_fails(self):
        """Uploading with wrong X-API-Key must return 401 Unauthorized."""
        payload = b"encrypted chunk blob with wrong key"
        headers = {AuthManager.API_KEY_HEADER: "wrong_fake_key_999"}
        res = self.session.post(f"{self.base_url}/upload/chunk_0.enc", data=payload, headers=headers)
        self.assertEqual(res.status_code, 401)

    def test_upload_and_download_with_valid_api_key_succeeds(self):
        """Uploading and downloading with correct X-API-Key must succeed."""
        test_payload = b"AUTHENTICATED_AES256_CHUNK_PAYLOAD_DATA" * 50
        headers = {AuthManager.API_KEY_HEADER: self.test_api_key}

        # 1. Upload
        upload_res = self.session.post(
            f"{self.base_url}/upload/test_chunk_42.enc",
            data=test_payload,
            headers=headers
        )
        self.assertEqual(upload_res.status_code, 200)
        self.assertEqual(upload_res.json()["status"], "success")

        # 2. Download without key -> 401
        dl_fail = self.session.get(f"{self.base_url}/download/test_chunk_42.enc")
        self.assertEqual(dl_fail.status_code, 401)

        # 3. Download with valid key -> 200 OK
        dl_success = self.session.get(
            f"{self.base_url}/download/test_chunk_42.enc",
            headers=headers
        )
        self.assertEqual(dl_success.status_code, 200)
        self.assertEqual(dl_success.content, test_payload)


if __name__ == "__main__":
    unittest.main()
