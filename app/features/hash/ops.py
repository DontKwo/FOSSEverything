"""File hashing and checksum verification. Zero external dependencies."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


SUPPORTED_ALGORITHMS = ["md5", "sha1", "sha256", "sha384", "sha512", "blake2b"]
CHUNK_SIZE = 1 << 20  # 1 MB


def hash_file(path: str, algorithm: str = "sha256", progress_cb: Callable[[int, int], None] | None = None) -> str:
    """Return hex digest of *path* using *algorithm*."""
    algo = algorithm.lower()
    if algo not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}. Choices: {SUPPORTED_ALGORITHMS}")

    h = hashlib.new(algo)
    file_size = os.path.getsize(path)
    bytes_read = 0

    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
            bytes_read += len(chunk)
            if progress_cb and file_size:
                progress_cb(bytes_read, file_size)

    return h.hexdigest()


def hash_text(text: str, algorithm: str = "sha256") -> str:
    """Return hex digest of UTF-8 encoded text."""
    algo = algorithm.lower()
    if algo not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    return hashlib.new(algo, text.encode("utf-8")).hexdigest()


def verify_hash(path: str, expected_hex: str, algorithm: str = "sha256") -> bool:
    """Return True when the file hash matches *expected_hex* (case-insensitive)."""
    actual = hash_file(path, algorithm)
    return actual.lower() == expected_hex.strip().lower()


def compare_files(path_a: str, path_b: str, algorithm: str = "sha256") -> bool:
    """Return True when two files share the same digest for the chosen algorithm."""
    return hash_file(path_a, algorithm).lower() == hash_file(path_b, algorithm).lower()


def hmac_digest(message: str | bytes, key: str | bytes, algorithm: str = "sha256") -> str:
    """Return a keyed digest (HMAC) for a byte string or UTF-8 text payload."""
    algo = algorithm.lower()
    if algo not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}. Choices: {SUPPORTED_ALGORITHMS}")
    if isinstance(message, str):
        message_bytes = message.encode("utf-8")
    else:
        message_bytes = message
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = key
    return hmac.new(key_bytes, message_bytes, getattr(hashlib, algo)).hexdigest()


def verify_hmac(message: str | bytes, key: str | bytes, expected_hex: str, algorithm: str = "sha256") -> bool:
    """Verify a keyed HMAC digest using a case-insensitive comparison."""
    actual = hmac_digest(message, key, algorithm)
    return actual.lower() == expected_hex.strip().lower()


def multi_hash_file(path: str, algorithms: list[str] | None = None) -> dict[str, str]:
    """Return a mapping of algorithm -> hex digest computed in a single pass."""
    if algorithms is None:
        algorithms = ["md5", "sha1", "sha256"]
    algorithms = [a.lower() for a in algorithms]
    hashers = {algo: hashlib.new(algo) for algo in algorithms}
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            for h in hashers.values():
                h.update(chunk)
    return {algo: h.hexdigest() for algo, h in hashers.items()}


# ─── Directory Hashing & Manifest Generation / Verification ──────────────────
def hash_directory_tree(dir_path: str, algorithm: str = "sha256", progress_cb: Callable[[int, int, int, int], None] | None = None) -> dict[str, Any]:
    """Recursively hash all files in *dir_path*."""
    algo = algorithm.lower()
    if algo not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    dir_path = os.path.abspath(dir_path)
    all_files = []
    total_bytes = 0
    results = []

    for root, _, filenames in os.walk(dir_path):
        for fname in sorted(filenames):
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, dir_path).replace("\\", "/")
            try:
                sz = os.path.getsize(full)
                all_files.append((rel, full, sz))
                total_bytes += sz
            except OSError as exc:
                results.append({
                    "rel_path": rel,
                    "full_path": full,
                    "hash": "",
                    "size": 0,
                    "status": f"Error: {exc}",
                })

    processed_bytes = 0

    for idx, (rel, full, sz) in enumerate(all_files):
        try:
            digest = hash_file(full, algo)
            results.append({
                "rel_path": rel,
                "full_path": full,
                "hash": digest,
                "size": sz,
                "status": "OK",
            })
        except Exception as exc:
            results.append({
                "rel_path": rel,
                "full_path": full,
                "hash": "",
                "size": sz,
                "status": f"Error: {exc}",
            })
        processed_bytes += sz
        if progress_cb:
            progress_cb(idx + 1, len(all_files), processed_bytes, total_bytes)

    return {
        "dir_path": dir_path,
        "algorithm": algo,
        "files": results,
        "total_files": len(results),
        "total_bytes": total_bytes,
    }


def generate_checksum_manifest(dir_path: str, output_manifest_path: str, algorithm: str = "sha256", progress_cb: Callable[[int, int, int, int], None] | None = None) -> str:
    """Hash directory tree and write standard GNU/BSD format manifest file."""
    res = hash_directory_tree(dir_path, algorithm=algorithm, progress_cb=progress_cb)
    lines = [f"# Checksum manifest generated by FOSSEverything ({algorithm.upper()})"]
    for item in res["files"]:
        if item["status"] == "OK":
            lines.append(f"{item['hash']}  {item['rel_path']}")

    with open(output_manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return output_manifest_path


def infer_algorithm_from_digest_length(digest_len: int) -> str:
    """Infer likely algorithm from hex length."""
    if digest_len == 32:
        return "md5"
    elif digest_len == 40:
        return "sha1"
    elif digest_len == 64:
        return "sha256"
    elif digest_len == 96:
        return "sha384"
    elif digest_len == 128:
        return "sha512"
    return "sha256"


def verify_checksum_manifest(manifest_path: str, base_dir: str | None = None, progress_cb: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    """Verify all files declared in a checksum manifest."""
    manifest_path = os.path.abspath(manifest_path)
    if base_dir is None:
        base_dir = os.path.dirname(manifest_path)
    base_dir = os.path.abspath(base_dir)

    entries = []
    with open(manifest_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format: <hash>  <filename> or <hash> *<filename>
            parts = line.split(None, 1)
            if len(parts) == 2:
                digest = parts[0].strip()
                rel = parts[1].lstrip("* ").strip().replace("\\", "/")
                entries.append((digest, rel))

    results = []
    passed = 0
    failed = 0
    missing = 0

    for idx, (expected_hash, rel_path) in enumerate(entries):
        full_path = os.path.join(base_dir, rel_path)
        algo = infer_algorithm_from_digest_length(len(expected_hash))

        if not os.path.exists(full_path):
            results.append({
                "rel_path": rel_path,
                "full_path": full_path,
                "expected": expected_hash,
                "actual": "",
                "status": "MISSING",
            })
            missing += 1
        else:
            try:
                actual_hash = hash_file(full_path, algo)
                if actual_hash.lower() == expected_hash.lower():
                    results.append({
                        "rel_path": rel_path,
                        "full_path": full_path,
                        "expected": expected_hash,
                        "actual": actual_hash,
                        "status": "PASS",
                    })
                    passed += 1
                else:
                    results.append({
                        "rel_path": rel_path,
                        "full_path": full_path,
                        "expected": expected_hash,
                        "actual": actual_hash,
                        "status": "FAILED",
                    })
                    failed += 1
            except Exception as exc:
                results.append({
                    "rel_path": rel_path,
                    "full_path": full_path,
                    "expected": expected_hash,
                    "actual": "",
                    "status": f"UNREADABLE ({exc})",
                })
                failed += 1

        if progress_cb:
            progress_cb(idx + 1, len(entries))

    return {
        "manifest_path": manifest_path,
        "base_dir": base_dir,
        "total": len(entries),
        "passed": passed,
        "failed": failed,
        "missing": missing,
        "results": results,
    }


# ─── Manifest Diffing ─────────────────────────────────────────────────────────
def parse_manifest(manifest_path: str) -> dict[str, str]:
    """Parse a .sha256/.md5/checksums.txt manifest into {rel_path: hex_digest}."""
    entries: dict[str, str] = {}
    with open(manifest_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                digest = parts[0].strip()
                rel = parts[1].lstrip("* ").strip().replace("\\", "/")
                entries[rel] = digest.lower()
    return entries


def diff_manifests(manifest_a: str, manifest_b: str) -> dict[str, Any]:
    """Compare two checksum manifests and report added, removed, and changed files."""
    entries_a = parse_manifest(manifest_a)
    entries_b = parse_manifest(manifest_b)

    added = sorted(set(entries_b) - set(entries_a))
    removed = sorted(set(entries_a) - set(entries_b))
    common = set(entries_a) & set(entries_b)
    changed = sorted(rel for rel in common if entries_a[rel] != entries_b[rel])

    return {
        "manifest_a": manifest_a,
        "manifest_b": manifest_b,
        "added": added,
        "removed": removed,
        "changed": [{"rel_path": rel, "old_hash": entries_a[rel], "new_hash": entries_b[rel]} for rel in changed],
        "unchanged_count": len(common) - len(changed),
    }


# ─── Content Signing ──────────────────────────────────────────────────────────
def generate_signing_keypair() -> tuple[bytes, bytes]:
    """Generate a new local Ed25519 keypair; returns (private_pem, public_pem)."""
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def save_signing_keypair(private_path: str, public_path: str) -> None:
    """Generate and save a new signing keypair to two local PEM files."""
    private_pem, public_pem = generate_signing_keypair()
    with open(private_path, "wb") as f:
        f.write(private_pem)
    with open(public_path, "wb") as f:
        f.write(public_pem)


def sign_file(path: str, private_key_pem: bytes | str) -> str:
    """Sign a file's SHA-256 digest with an Ed25519 private key; returns a base64 signature."""
    if isinstance(private_key_pem, str):
        private_key_pem = private_key_pem.encode("utf-8")
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    digest = bytes.fromhex(hash_file(path, "sha256"))
    signature = private_key.sign(digest)
    return base64.b64encode(signature).decode("ascii")


def verify_signature(path: str, signature_b64: str, public_key_pem: bytes | str) -> bool:
    """Verify a base64 Ed25519 signature against a file's SHA-256 digest."""
    if isinstance(public_key_pem, str):
        public_key_pem = public_key_pem.encode("utf-8")
    public_key = serialization.load_pem_public_key(public_key_pem)
    digest = bytes.fromhex(hash_file(path, "sha256"))
    signature = base64.b64decode(signature_b64)
    try:
        public_key.verify(signature, digest)
        return True
    except InvalidSignature:
        return False


# ─── Signature Timestamping ───────────────────────────────────────────────────
def _timestamped_payload(file_hash: str, timestamp: str, signer_name: str | None) -> bytes:
    """Build the canonical payload that gets signed/verified for a timestamped signature."""
    return f"{file_hash}|{timestamp}|{signer_name or ''}".encode("utf-8")


def sign_file_with_timestamp(path: str, private_key_pem: bytes | str, signer_name: str | None = None) -> dict[str, Any]:
    """Sign a file's hash together with a local UTC timestamp (and optional signer name).

    This is a local attestation of "this hash existed at this local-clock time," not a
    third-party-notarized RFC 3161 timestamp (that would require a network Time-Stamping
    Authority call, which this local-first app does not make).
    """
    if isinstance(private_key_pem, str):
        private_key_pem = private_key_pem.encode("utf-8")
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    file_hash = hash_file(path, "sha256")
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = _timestamped_payload(file_hash, timestamp, signer_name)
    signature = private_key.sign(payload)

    return {
        "file_hash": file_hash,
        "timestamp": timestamp,
        "signer_name": signer_name,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def verify_timestamped_signature(bundle: dict[str, Any], public_key_pem: bytes | str, path: str) -> dict[str, Any]:
    """Verify a timestamped signature bundle against *path*'s current contents.

    Reports signature validity and current-hash-match separately so a caller can tell
    "the signature is invalid" apart from "the file changed since it was signed."
    """
    if isinstance(public_key_pem, str):
        public_key_pem = public_key_pem.encode("utf-8")
    public_key = serialization.load_pem_public_key(public_key_pem)

    file_hash = bundle["file_hash"]
    timestamp = bundle["timestamp"]
    signer_name = bundle.get("signer_name")
    payload = _timestamped_payload(file_hash, timestamp, signer_name)
    signature = base64.b64decode(bundle["signature"])

    try:
        public_key.verify(signature, payload)
        signature_valid = True
    except InvalidSignature:
        signature_valid = False

    current_hash = hash_file(path, "sha256")

    return {
        "signature_valid": signature_valid,
        "hash_matches": current_hash.lower() == file_hash.lower(),
        "timestamp": timestamp,
        "signer_name": signer_name,
    }


# ─── Trusted-Key Management ───────────────────────────────────────────────────
def _trusted_keys_path() -> str:
    """Return the local file path where named trusted public keys are persisted."""
    config_dir = os.path.join(os.path.expanduser("~"), ".fosseverything")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "trusted_keys.json")


def list_trusted_keys() -> dict[str, str]:
    """Return {name: public_key_pem} for every locally stored trusted key."""
    path = _trusted_keys_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def add_trusted_key(name: str, public_key_pem: str) -> None:
    """Add or replace a named trusted public key in the local keyring."""
    keys = list_trusted_keys()
    keys[name] = public_key_pem
    with open(_trusted_keys_path(), "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2)


def remove_trusted_key(name: str) -> None:
    """Remove a named trusted public key from the local keyring, if present."""
    keys = list_trusted_keys()
    if name in keys:
        del keys[name]
        with open(_trusted_keys_path(), "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)


# ─── Policy-Based Verification Presets ────────────────────────────────────────
VERIFICATION_POLICY_PRESETS: dict[str, dict[str, Any]] = {
    "Quick Check": {
        "description": "Fast single-algorithm check for casual local transfers.",
        "algorithm": "md5",
        "require_signature": False,
    },
    "Standard Release": {
        "description": "SHA-256 manifest verification for typical software releases.",
        "algorithm": "sha256",
        "require_signature": False,
    },
    "Signed Release": {
        "description": "SHA-256 manifest verification plus a mandatory Ed25519 signature check.",
        "algorithm": "sha256",
        "require_signature": True,
    },
    "Compliance Archive": {
        "description": "SHA-512 manifest verification plus a mandatory signature for long-term retention.",
        "algorithm": "sha512",
        "require_signature": True,
    },
}


def verification_policy_presets() -> dict[str, dict[str, Any]]:
    """Return named integrity-verification policy presets."""
    return VERIFICATION_POLICY_PRESETS


def apply_verification_policy(
    policy_name: str,
    manifest_path: str,
    base_dir: str | None = None,
    signature_path: str | None = None,
    public_key_path: str | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Run manifest verification under a named policy, enforcing its signature requirement."""
    policy = VERIFICATION_POLICY_PRESETS.get(policy_name)
    if policy is None:
        raise ValueError(f"Unknown verification policy: {policy_name}")

    result = verify_checksum_manifest(manifest_path, base_dir=base_dir, progress_cb=progress_cb)
    result["policy"] = policy_name
    result["signature_required"] = policy["require_signature"]
    result["signature_verified"] = None

    if policy["require_signature"]:
        if not signature_path or not public_key_path:
            result["signature_verified"] = False
            result["signature_error"] = "This policy requires a signature and public key, but none was provided."
        else:
            with open(signature_path, "r", encoding="utf-8") as f:
                signature_b64 = f.read().strip()
            with open(public_key_path, "rb") as f:
                public_key_pem = f.read()
            result["signature_verified"] = verify_signature(manifest_path, signature_b64, public_key_pem)

    return result



