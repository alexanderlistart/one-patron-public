#!/usr/bin/env python3
"""Offline handoff tests using only public pinned bytes and synthetic builds."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from favicon_gate import binding, load_policy, render_favicon_links, stamp


HERE = Path(__file__).resolve().parent
SITE = HERE.parents[1] / "site"
PROFILE_NAME = "favicon-policy-v0.1.json"
FINALIZER_NAME = "finalize-candidate.py"
PROFILE = load_policy()
PIN_RE = re.compile(rb'(?m)^PROFILE_SHA256 = "([0-9a-f]{64})"$')
EXCEPTIONS = PROFILE["historical_exceptions"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compare_installs(other):
    """Detect drift while allowing the documented edition metadata and policy pin."""
    other = Path(other).resolve()
    require((HERE / "favicon_gate.py").read_bytes() == (other / "favicon_gate.py").read_bytes(),
            "validator/renderer bytes differ")

    def behavior(install):
        policy_bytes = (install / PROFILE_NAME).read_bytes()
        finalizer_bytes = (install / FINALIZER_NAME).read_bytes()
        pins = PIN_RE.findall(finalizer_bytes)
        digest = sha256(policy_bytes).hexdigest().encode("ascii")
        require(pins == [digest], "finalizer does not pin its own policy bytes")
        policy = load_policy(install / PROFILE_NAME)
        for key in ("status", "reference"):
            policy.pop(key, None)
        for record in policy["historical_exceptions"].values():
            record.pop("authority", None)
        return policy, PIN_RE.sub(b'PROFILE_SHA256 = "<verified own digest>"', finalizer_bytes)

    public_policy, public_finalizer = behavior(HERE)
    other_policy, other_finalizer = behavior(other)
    require(public_policy == other_policy, "operative policy or immutable bindings differ")
    require(public_finalizer == other_finalizer, "finalizer code differs outside the policy digest")


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pins = {asset["link"]["href"][1:]: asset for asset in PROFILE["assets"].values()}
        for name, record in EXCEPTIONS.items():
            pins[name] = record
            pins.update(record["protected_dependencies"])
        cls.pinned_files = {}
        for path, record in pins.items():
            data = (SITE / path).read_bytes()
            require(stamp(data) == binding(record), f"public fixture differs from reviewed policy: {path}")
            cls.pinned_files[path] = data

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="one-patron-favicon-test-")
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name).resolve()
        self.root = self.work / "generated"
        self.root.mkdir()
        for path, data in self.pinned_files.items():
            self.write(path, data)
        self.ico, self.svg = render_favicon_links(PROFILE).splitlines()
        self.add_page("existing/index.html", self.ico, self.svg)
        self.add_page("retained/index.html", self.svg)
        files = {item.relative_to(self.root).as_posix(): stamp(item.read_bytes())
                 for item in self.root.rglob("*") if item.is_file()}
        self.baseline = self.work / "baseline.json"
        data = json.dumps({"generated": files}, sort_keys=True, separators=(",", ":")).encode("ascii")
        self.baseline.write_bytes(data)
        self.baseline_pin = sha256(data).hexdigest()

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def add_page(self, path, *links):
        page = ("<!doctype html>\n<html lang=\"en\"><head><title>Fixture</title>\n"
                + "\n".join(links) + "\n</head><body>Test page.</body></html>\n")
        return self.write(path, page.encode("utf-8"))

    def finalize(self, *extra, pin=None, baseline=None):
        args = [
            sys.executable, "-B", str(HERE / FINALIZER_NAME), "--root", str(self.root),
            "--baseline-inventory", str(baseline or self.baseline),
            "--baseline-sha256", pin if pin is not None else self.baseline_pin, *extra,
        ]
        return subprocess.run(args, cwd=self.work, capture_output=True, text=True, check=False)

    def passed(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["status"], "FAVICON_GATE_PASS")
        self.assertEqual(receipt["policy_sha256"], sha256((HERE / PROFILE_NAME).read_bytes()).hexdigest())
        self.assertEqual(receipt["baseline_inventory_sha256"], self.baseline_pin)
        return receipt

    def blocked(self, result, diagnostic):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("FAVICON_GATE_FAIL:", result.stderr)
        self.assertIn(diagnostic, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_public_pins_and_unchanged_incremental_boundary(self):
        receipt = self.passed(self.finalize())
        self.assertEqual(receipt["added_or_modified_html"], 0)
        self.assertEqual(receipt["checked_pages"], dict.fromkeys(EXCEPTIONS, "PASS_FROZEN_EXACT"))

    def test_new_output_passes_and_receipt_rechecks(self):
        self.add_page("new/depth/index.html", self.ico, self.svg)
        receipt = self.passed(self.finalize())
        self.assertEqual(receipt["added_or_modified_html"], 1)
        self.assertEqual(receipt["checked_pages"]["new/depth/index.html"], "PASS_PROFILE")
        self.assertEqual(self.passed(self.finalize("--expect-candidate-sha256", receipt["candidate_sha256"])), receipt)

    def test_discovers_new_and_changed_outputs_without_a_supplied_list(self):
        self.add_page("new/incomplete.htm", self.svg)
        self.blocked(self.finalize(), "new/incomplete.htm: wrong, duplicated or incomplete favicon sequence")
        self.add_page("new/incomplete.htm", self.ico, self.svg)
        self.add_page("existing/index.html", self.svg)
        self.blocked(self.finalize(), "existing/index.html: wrong, duplicated or incomplete favicon sequence")
        self.add_page("existing/index.html", self.ico, self.svg, "<meta name=\"test\" content=\"updated\">")
        receipt = self.passed(self.finalize())
        self.assertEqual(receipt["added_or_modified_html"], 2)

    def test_declarations_are_strict(self):
        pairs = [
            ((self.svg, self.ico), "sequence"),
            ((self.ico, self.ico, self.svg), "sequence"),
            ((self.ico.replace("image/x-icon", "image/png"), self.svg), "attribute(s): type"),
            ((self.ico, self.svg.replace('sizes="any"', 'sizes="16x16"')), "attribute(s): sizes"),
            ((self.ico, self.svg.replace("/favicon-v2.svg", "https://example.invalid/favicon-v2.svg")), "root-relative"),
            ((self.ico, self.svg.replace("/favicon-v2.svg", "/favicon-v2.svg?fixture=1")), "root-relative"),
            (('<base href="https://example.invalid/">', self.ico, self.svg), "can change favicon URL resolution"),
        ]
        for links, diagnostic in pairs:
            with self.subTest(diagnostic=diagnostic, links=links):
                self.add_page("new/demo.html", *links)
                self.blocked(self.finalize(), diagnostic)

    def test_optional_icons_use_existing_pinned_bytes(self):
        self.add_page("new/ancillary.html", render_favicon_links(PROFILE, ("touch", "mask")))
        self.assertEqual(self.passed(self.finalize())["checked_pages"]["new/ancillary.html"], "PASS_PROFILE")
        (self.root / "apple-touch-icon-v2.png").unlink()
        self.blocked(self.finalize(), "missing generated file: apple-touch-icon-v2.png")

    def test_missing_or_substituted_required_asset_stops_even_with_no_new_html(self):
        icon = self.root / "favicon-v2.ico"
        icon.unlink()
        self.blocked(self.finalize(), "missing generated file: favicon-v2.ico")
        icon.write_bytes(self.pinned_files["favicon-v2.ico"] + b"changed")
        self.blocked(self.finalize(), "asset bytes/size drift: /favicon-v2.ico")

    def test_frozen_rewrite_rejected_at_each_registered_path(self):
        for path in EXCEPTIONS:
            with self.subTest(path=path):
                self.add_page(path, self.ico, self.svg)
                self.blocked(self.finalize(), f"{path}: frozen HTML hash mismatch")
                self.write(path, self.pinned_files[path])

    def test_exception_does_not_transfer_to_another_path(self):
        frozen = next(path for path in EXCEPTIONS if "to-be-known" in path)
        self.write("new/unregistered.html", self.pinned_files[frozen])
        self.blocked(self.finalize(), "new/unregistered.html:")

    def test_frozen_removal_and_dependency_drift_fail_closed(self):
        path = next(iter(EXCEPTIONS))
        (self.root / path).unlink()
        self.blocked(self.finalize(), "HTML removal is not authorized")
        self.write(path, self.pinned_files[path])
        self.write("depth/depth.css", b"unapproved")
        self.blocked(self.finalize(), "frozen dependency changed: depth/depth.css")

    def test_baseline_digest_and_frozen_identity_are_verified(self):
        self.blocked(self.finalize(pin="0" * 64), "inventory digest differs from trusted pin")
        data = json.loads(self.baseline.read_bytes())
        path = next(iter(EXCEPTIONS))
        data["generated"][path]["sha256"] = "0" * 64
        edited = json.dumps(data, sort_keys=True).encode("ascii")
        self.baseline.write_bytes(edited)
        self.blocked(self.finalize(pin=sha256(edited).hexdigest()), "historical path is not established by this baseline")

    def test_inventory_cannot_be_inside_candidate(self):
        local = self.write("baseline-copy.json", self.baseline.read_bytes())
        self.blocked(self.finalize(baseline=local), "baseline inventory belongs outside")

    def test_post_pass_non_html_change_invalidates_handoff(self):
        receipt = self.passed(self.finalize())
        self.write("extra.txt", b"unsealed change")
        self.blocked(self.finalize("--expect-candidate-sha256", receipt["candidate_sha256"]),
                     "candidate digest differs from accepted handoff")

    def test_wrangler_config_must_point_to_same_tree(self):
        config = self.work / "wrangler.jsonc"
        config.write_text('{"assets":{"directory":"./generated"}}', encoding="utf-8")
        args = ("--wrangler-config", str(config))
        receipt = self.passed(self.finalize(*args))
        self.assertEqual(receipt["wrangler_config"], {"path": str(config),
                                                       "sha256": sha256(config.read_bytes()).hexdigest()})
        config.write_text('{"assets":{"directory":"./different"}}', encoding="utf-8")
        self.blocked(self.finalize(*args), "not verified root")
        config.write_text('{"assets":{"directory":"./generated"},"env":{"prod":{}}}', encoding="utf-8")
        self.blocked(self.finalize(*args), "environment-specific Wrangler configs are outside")

    def test_symlink_is_rejected(self):
        (self.root / "favicon-alias.ico").symlink_to(self.root / "favicon-v2.ico")
        self.blocked(self.finalize(), "not a regular generated file: favicon-alias.ico")

    def test_copy_parity_rejects_operative_policy_change_even_if_repinned(self):
        other = self.work / "second-install"
        other.mkdir()
        for name in (PROFILE_NAME, FINALIZER_NAME, "favicon_gate.py"):
            (other / name).write_bytes((HERE / name).read_bytes())
        compare_installs(other)
        policy = json.loads((other / PROFILE_NAME).read_bytes())
        policy["required_order"].reverse()
        changed = json.dumps(policy).encode("utf-8")
        (other / PROFILE_NAME).write_bytes(changed)
        tool = other / FINALIZER_NAME
        tool.write_bytes(PIN_RE.sub(b'PROFILE_SHA256 = "' + sha256(changed).hexdigest().encode("ascii") + b'"',
                                    tool.read_bytes()))
        with self.assertRaisesRegex(ValueError, "operative policy or immutable bindings differ"):
            compare_installs(other)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare-install", type=Path,
                        help="first require functional parity with a second installed gate directory")
    args = parser.parse_args()
    if args.compare_install:
        try:
            compare_installs(args.compare_install)
        except (OSError, KeyError, ValueError) as error:
            sys.exit(f"FAVICON_GATE_PARITY_FAIL: {error}")
        print("FAVICON_GATE_PARITY_PASS")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Integration))
    sys.exit(not result.wasSuccessful())
