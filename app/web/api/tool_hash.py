from pathlib import Path
from typing import Any

from app.features.hash.ops import (
    SUPPORTED_ALGORITHMS,
    add_trusted_key,
    apply_verification_policy,
    compare_files,
    diff_manifests,
    generate_checksum_manifest,
    hash_directory_tree,
    hash_file,
    hash_text,
    hmac_digest,
    list_trusted_keys,
    multi_hash_file,
    remove_trusted_key,
    save_signing_keypair,
    sign_file,
    sign_file_with_timestamp,
    verification_policy_presets,
    verify_checksum_manifest,
    verify_hash,
    verify_signature,
    verify_timestamped_signature,
)
from app.web.api.result import api_method, ok, require


class HashApiMixin:
    @api_method
    def hash_supported_algorithms(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return list of supported cryptographic hash algorithms.
        return ok(algorithms=list(SUPPORTED_ALGORITHMS))

    @api_method
    def hash_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compute cryptographic hash of single file.
        require(params, "file_path")
        file_path = str(params["file_path"])
        algo = str(params.get("algorithm", "sha256"))
        digest = hash_file(file_path, algorithm=algo)
        return ok(hash=digest, algorithm=algo, file_path=file_path)

    @api_method
    def compute_file_hash(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for file hash calculation.
        return self.hash_file(params)

    @api_method
    def compute_hash(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for file hash computation.
        return self.hash_file(params)

    @api_method
    def hash_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compute cryptographic hash of string.
        require(params, "text")
        text = str(params["text"])
        algo = str(params.get("algorithm", "sha256"))
        digest = hash_text(text, algorithm=algo)
        return ok(hash=digest, algorithm=algo)

    @api_method
    def compute_text_hash(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for text hash calculation.
        return self.hash_text(params)

    @api_method
    def hash_multi(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compute multiple hash algorithms simultaneously for a file.
        require(params, "file_path")
        file_path = str(params["file_path"])
        algos = list(params.get("algorithms", ["sha256", "md5", "sha1"]))
        hashes = multi_hash_file(file_path, algorithms=algos)
        return ok(hashes=hashes, file_path=file_path)

    @api_method
    def hash_compare_files(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compare checksums of two files to verify identity.
        require(params, "path1", "path2")
        algo = str(params.get("algorithm", "sha256"))
        identical, h1, h2 = compare_files(str(params["path1"]), str(params["path2"]), algorithm=algo)
        return ok(identical=identical, hash1=h1, hash2=h2, algorithm=algo)

    @api_method
    def hash_hmac(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compute HMAC signature of data using secret key.
        require(params, "data", "key")
        algo = str(params.get("algorithm", "sha256"))
        data_bytes = str(params["data"]).encode("utf-8")
        key_bytes = str(params["key"]).encode("utf-8")
        mac = hmac_digest(data_bytes, key_bytes, algorithm=algo)
        return ok(hmac=mac, algorithm=algo)

    @api_method
    def hash_verify(self, params: dict[str, Any]) -> dict[str, Any]:
        # Verify file digest against expected hash.
        require(params, "file_path", "expected_hash")
        file_path = str(params["file_path"])
        exp = str(params["expected_hash"]).strip()
        algo = str(params.get("algorithm", "sha256"))
        matches = verify_hash(file_path, exp, algorithm=algo)
        actual = hash_file(file_path, algorithm=algo)
        return ok(matches=matches, actual_hash=actual, expected_hash=exp, algorithm=algo)

    @api_method
    def verify_hash(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for hash verification.
        return self.hash_verify(params)

    @api_method
    def verify_checksum(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for checksum verification.
        return self.hash_verify(params)

    @api_method
    def hash_directory_tree(self, params: dict[str, Any]) -> dict[str, Any]:
        # Traverse folder and compute hashes for all contained files.
        require(params, "directory_path")
        dir_path = str(params["directory_path"])
        algo = str(params.get("algorithm", "sha256"))
        tree_res = hash_directory_tree(dir_path, algorithm=algo)
        files = tree_res.get("files", [])
        total_files = tree_res.get("total_files", len(files))
        out_manifest = params.get("output_manifest")
        if out_manifest:
            generate_checksum_manifest(files, str(out_manifest), algorithm=algo)
        return ok(entries=tree_res, files=files, count=total_files, algorithm=algo)

    @api_method
    def generate_manifest(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate checksum manifest file for directory contents.
        require(params, "directory_path")
        return self.hash_directory_tree(params)

    @api_method
    def hash_verify_manifest(self, params: dict[str, Any]) -> dict[str, Any]:
        # Verify checksum manifest file against directory files.
        require(params, "manifest_path")
        man_path = str(params["manifest_path"])
        base_dir = params.get("base_dir")
        summary = verify_checksum_manifest(man_path, base_dir=str(base_dir) if base_dir else None)
        return ok(summary=summary)

    @api_method
    def verify_manifest(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for manifest verification.
        return self.hash_verify_manifest(params)

    @api_method
    def verify_checksum_manifest(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for checksum manifest verification.
        return self.hash_verify_manifest(params)

    @api_method
    def hash_diff_manifests(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compare two checksum manifests and identify added, removed, or modified files.
        require(params, "manifest1_path", "manifest2_path")
        diff_res = diff_manifests(str(params["manifest1_path"]), str(params["manifest2_path"]))
        return ok(diff=diff_res)

    @api_method
    def hash_sign(self, params: dict[str, Any]) -> dict[str, Any]:
        # Sign file using private key and optional RFC 3161 timestamp.
        require(params, "file_path", "private_key_path")
        file_path = str(params["file_path"])
        key_path = str(params["private_key_path"])
        ts_url = params.get("timestamp_server_url")
        if ts_url:
            sig = sign_file_with_timestamp(file_path, key_path, str(ts_url))
        else:
            sig = sign_file(file_path, key_path)
        out_sig = params.get("output_sig_path")
        if out_sig:
            Path(str(out_sig)).write_text(sig, encoding="utf-8")
        return ok(signature=sig)

    @api_method
    def hash_verify_signature(self, params: dict[str, Any]) -> dict[str, Any]:
        # Verify Ed25519 digital signature of file.
        require(params, "file_path", "signature", "public_key")
        file_path = str(params["file_path"])
        sig = str(params["signature"])
        pk = str(params["public_key"])
        is_ts = bool(params.get("timestamped", False))
        if is_ts:
            valid, signer, ts = verify_timestamped_signature(file_path, sig, pk)
            return ok(valid=valid, signer=signer, timestamp=ts)
        valid = verify_signature(file_path, sig, pk)
        return ok(valid=valid)

    @api_method
    def hash_keys(self, params: dict[str, Any]) -> dict[str, Any]:
        # Manage trusted signing key list.
        action = str(params.get("action", "list")).lower()
        if action == "add":
            require(params, "name", "public_key")
            add_trusted_key(str(params["name"]), str(params["public_key"]))
        elif action == "remove":
            require(params, "name")
            remove_trusted_key(str(params["name"]))
        return ok(keys=list_trusted_keys())

    @api_method
    def hash_generate_keypair(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate new Ed25519 signing keypair and save to disk.
        require(params, "output_dir", "name")
        priv_p, pub_p = save_signing_keypair(str(params["output_dir"]), str(params["name"]))
        return ok(private_key_path=priv_p, public_key_path=pub_p)

    @api_method
    def hash_policy_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Query verification policy presets or evaluate policy.
        presets = verification_policy_presets()
        policy_name = params.get("policy")
        if policy_name and "results" in params:
            passed, violations = apply_verification_policy(str(policy_name), list(params["results"]))
            return ok(passed=passed, violations=violations, presets=presets)
        return ok(presets=presets)
