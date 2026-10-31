"""
Module: core.auth
Author: Shlok Shah (@ShlokShah2007)
Purpose: Storage Node API Key Authentication & Verification
"""

import os
import hmac
import secrets


class AuthManager:
    """
    Manages API key authentication between the Client and Storage Nodes.
    """

    API_KEY_HEADER = "X-API-Key"

    @staticmethod
    def generate_api_key(prefix: str = "chunk_sec_key_") -> str:
        """Generates a secure random 32-character hexadecimal API key."""
        random_token = secrets.token_hex(16)
        return f"{prefix}{random_token}"

    @staticmethod
    def verify_api_key(incoming_key: str, expected_key: str) -> bool:
        """
        Constant-time string comparison to protect against timing side-channel attacks.
        """
        if not incoming_key or not expected_key:
            return False
        return hmac.compare_digest(incoming_key.strip(), expected_key.strip())
