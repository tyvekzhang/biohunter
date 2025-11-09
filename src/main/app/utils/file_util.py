# SPDX-License-Identifier: MIT
"""File relate util"""
import hashlib


def calculate_file_sha256(file_path: str) -> str:
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def calculate_chunk_sha256(content: bytes) -> str:
    """Calculate SHA-256 hash of chunk content"""
    return hashlib.sha256(content).hexdigest()