#!/usr/bin/env python3
"""Fail-closed local handoff for the actual generated Worker asset tree."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
from xml.etree import ElementTree

from favicon_gate import Gate, GateError, HASH, POLICY, load_policy, need, relative

PROFILE_SHA256 = "f9bbaee09cba51210e8a6e6fce2c3043099a2d5ad80551abf26586a5d0713250"


def snapshot(root):
    def cannot_read(error):
        raise error

    records = {}
    for parent, dirs, files in os.walk(root, onerror=cannot_read, followlinks=False):
        base = Path(parent)
        for name in dirs:
            item = base / name
            need(stat.S_ISDIR(item.lstat().st_mode), f"not a real generated directory: {item}")
        for name in files:
            item = base / name
            path = relative(item.relative_to(root).as_posix()).as_posix()
            need(stat.S_ISREG(item.lstat().st_mode), f"not a regular generated file: {path}")
            size = 0
            digest = sha256()
            with item.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    size += len(chunk)
                    digest.update(chunk)
            records[path] = {"bytes": size, "sha256": digest.hexdigest()}
    need(records, "empty generated candidate")
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("ascii")
    return len(records), sha256(encoded).hexdigest()


def verify_config(config, root):
    source = Path(config)
    need(source.is_file() and not source.is_symlink(), "expected a real Wrangler config")
    source = source.resolve()
    data = source.read_bytes()
    try:
        settings = json.loads(data)
    except ValueError as ex:
        raise GateError("Wrangler handoff requires a JSON-compatible config, without comments or trailing commas") from ex
    need(isinstance(settings, dict), "expected a Wrangler config object")
    need(not settings.get("env"), "environment-specific Wrangler configs are outside this local handoff")
    directory = settings["assets"]["directory"]
    need(isinstance(directory, str) and bool(directory.strip()), "missing Wrangler assets.directory")
    configured = (source.parent / directory).resolve()
    need(configured == root, f"Wrangler assets.directory resolves to {configured}, not verified root {root}")
    return {"path": str(source), "sha256": sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="exact generated assets.directory, not the raw source")
    parser.add_argument("--baseline-inventory", required=True)
    parser.add_argument("--baseline-sha256", required=True, help="pin from the last accepted release receipt")
    parser.add_argument("--expect-candidate-sha256", help="recheck the earlier handoff digest before any next step")
    parser.add_argument("--wrangler-config", help="for Wrangler handoff, verify this config resolves to the same tree")
    args = parser.parse_args()
    try:
        need(sha256(POLICY.read_bytes()).hexdigest() == PROFILE_SHA256, "favicon policy differs from approved pin")
        if args.expect_candidate_sha256 is not None:
            need(HASH.fullmatch(args.expect_candidate_sha256), "invalid expected candidate SHA-256")
        policy = load_policy()
        gate = Gate(args.root, policy)
        config = verify_config(args.wrangler_config, gate.root) if args.wrangler_config else None
        baseline = Path(args.baseline_inventory).resolve()
        need(not baseline.is_relative_to(gate.root), "baseline inventory belongs outside the generated candidate")
        before = snapshot(gate.root)
        for key in policy["required_order"]:
            gate.asset(key)
        paths, changed_html, total_html = gate.release_scope(baseline, args.baseline_sha256)
        pages = {}
        for path in paths:
            try:
                pages[path] = gate.page(path)
            except (OSError, ValueError, ElementTree.ParseError) as ex:
                raise GateError(f"{path}: {ex}") from ex
        need(snapshot(gate.root) == before, "candidate changed during verification; stop and inspect")
        if config:
            need(sha256(Path(config["path"]).read_bytes()).hexdigest() == config["sha256"],
                 "Wrangler config changed during verification")
        count, candidate_hash = before
        if args.expect_candidate_sha256 is not None:
            need(candidate_hash == args.expect_candidate_sha256,
                 f"candidate digest differs from accepted handoff: {candidate_hash}")
        print(json.dumps({
            "schema": 1,
            "status": "FAVICON_GATE_PASS",
            "policy_version": policy["version"],
            "policy_sha256": PROFILE_SHA256,
            "baseline_inventory_sha256": args.baseline_sha256,
            "generated_root": str(gate.root),
            "candidate_sha256": candidate_hash,
            "generated_files": count,
            "generated_html": total_html,
            "added_or_modified_html": changed_html,
            "checked_pages": pages,
            "wrangler_config": config,
        }, indent=2, sort_keys=True))
        return 0
    except (OSError, GateError, KeyError, TypeError, ValueError, ElementTree.ParseError) as ex:
        print(f"FAVICON_GATE_FAIL: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
