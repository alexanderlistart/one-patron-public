#!/usr/bin/env python3
"""Read-only favicon validation for final static HTML; no dependencies or network."""

import argparse
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
from struct import unpack_from
import sys
from xml.etree import ElementTree

POLICY = Path(__file__).with_name("favicon-policy-v0.1.json")
HASH = re.compile(r"[a-f0-9]{64}\Z")
HTML_SUFFIXES = {".html", ".htm"}
HEAD_TAGS = {"base", "link", "meta", "noscript", "script", "style", "template", "title"}


class GateError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise GateError(message)


def relative(value):
    p = PurePosixPath(value)
    need(bool(p.parts) and not p.is_absolute() and p.as_posix() == value
         and ".." not in p.parts and "\\" not in value and not any(ord(c) < 32 for c in value),
         f"not a canonical final-tree relative path: {value!r}")
    return p


def safe_href(value):
    need(value.startswith("/") and not value.startswith("//") and not any(c in value for c in "?#%"),
         f"icon URL must be root-relative and literal: {value!r}")
    return relative(value[1:]).as_posix()


def binding(record):
    need(type(record.get("bytes")) is int and record["bytes"] >= 0
         and isinstance(record.get("sha256"), str) and HASH.fullmatch(record["sha256"]),
         "invalid size/SHA-256 record")
    return {"bytes": record["bytes"], "sha256": record["sha256"]}


def stamp(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def load_policy(file=POLICY):
    policy = json.loads(Path(file).read_bytes())
    need(policy["schema"] == 1 and policy["policy_id"] == "ONE_PATRON_SHARED_FAVICON",
         "unknown favicon policy schema or identity")
    order = policy["required_order"] + policy["optional_order"]
    need(bool(policy["required_order"]) and sorted(order) == sorted(policy["assets"]),
         "invalid or duplicate asset profile keys")
    urls = []
    for asset in policy["assets"].values():
        a = asset["link"]
        urls.append(safe_href(a["href"]))
        binding(asset)
        need({"ico-png": "image/x-icon", "svg": "image/svg+xml", "png": "image/png"}.get(asset["format"])
             == asset["mime"] and a.get("type", asset["mime"]) == asset["mime"],
             f"invalid MIME mapping for {a['href']}")
        sizes = " ".join(f"{w}x{h}" for w, h in asset.get("dimensions", [])) or "any"
        if "sizes" in a:
            need(a["sizes"] == sizes, f"policy sizes do not match file descriptors: {a['href']}")
    need(len(set(urls)) == len(urls), "duplicate policy asset URL")
    for path, x in policy["historical_exceptions"].items():
        relative(path)
        binding(x)
        need(bool(x["reason"]) and bool(x["authority"]), f"historical reason/evidence missing: {path}")
        for link in x["observed_links"]:
            need(safe_href(link["href"]) in urls, f"historical icon asset not pinned: {path}")
        for p, b in x["protected_dependencies"].items():
            relative(p)
            binding(b)
    return policy


def render_favicon_links(policy, include=()):
    """Return only the favicon fragment. Call before sealing a new HTML document."""
    selection = list(include)
    allowed = policy["optional_order"]
    need(len(selection) == len(set(selection)) and set(selection) <= set(allowed),
         "duplicate or unsupported ancillary icon ID")
    order = policy["required_order"] + [x for x in allowed if x in selection]
    return "\n".join(
        "  <link " + " ".join(f'{key}="{escape(value, quote=True)}"'
                              for key, value in policy["assets"][name]["link"].items()) + ">"
        for name in order)


class FaviconHead(HTMLParser):
    def __init__(self, data, rels):
        super().__init__(convert_charrefs=True)
        self.rels = rels
        self.active = False
        self.heads = 0
        self.body_seen = False
        self.inert = []
        self.links = []
        self.feed(data.decode("utf-8"))
        self.close()
        need(self.heads == 1 and not self.active and not self.inert,
             "expected one explicit closed <head> and balanced inert sections")

    def handle_starttag(self, tag, attrs):
        if self.inert and self.inert[-1] == "title":
            return
        if tag == "head":
            self.heads += 1
            need(self.heads == 1 and not self.inert and not self.body_seen,
                 "duplicate, nested or late <head>")
            self.active = True
        elif self.active and not self.inert:
            need(tag in HEAD_TAGS, f"<{tag}> implicitly ends <head>; favicon placement is not reliable")
        if tag == "body" and not self.inert:
            self.body_seen = True
        if tag == "base" and not self.inert:
            need(not any(k == "href" for k, _ in attrs),
                 "<base href> can change favicon URL resolution and is not allowed by this profile")
        if tag in {"template", "noscript", "title"}:
            self.inert.append(tag)
        if tag != "link" or not any(self.rels.intersection((v or "").lower().split())
                                    for k, v in attrs if k == "rel"):
            return
        need(self.active and not self.inert, "favicon-related link is outside the active <head>")
        a = dict(attrs)
        need(len(a) == len(attrs) and all(v is not None for v in a.values()),
             "duplicate or valueless favicon link attribute")
        self.links.append(a)

    def handle_endtag(self, tag):
        if self.inert and self.inert[-1] == "title" and tag != "title":
            return
        if tag == "head":
            need(self.active and not self.inert, "unexpected </head>")
            self.active = False
        elif tag in {"template", "noscript", "title"}:
            need(self.inert and self.inert[-1] == tag, f"unbalanced </{tag}>")
            self.inert.pop()


def png_dimensions(data):
    need(len(data) >= 33 and data[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR",
         "not a PNG with an IHDR header")
    return list(unpack_from(">II", data, 16))


def inspect_format(data, asset):
    kind = asset["format"]
    if kind == "ico-png":
        need(len(data) > 6, "truncated ICO")
        reserved, kind_code, count = unpack_from("<HHH", data, 0)
        end = 6 + 16 * count
        need(reserved == 0 and kind_code == 1 and count == len(asset["dimensions"]) and end <= len(data),
             "invalid ICO type, entry count or table")
        frames = []
        for i in range(count):
            x = 6 + 16 * i
            w, h, palette, zero, planes, bits, length, offset = unpack_from("<BBBBHHII", data, x)
            size = [w or 256, h or 256]
            need(zero == 0 and offset >= end and offset + length <= len(data)
                 and png_dimensions(data[offset:offset + length]) == size, "invalid ICO PNG frame")
            frames.append(size)
        need(frames == asset["dimensions"], f"ICO frame sizes/order: {frames!r}")
    elif kind == "png":
        need([png_dimensions(data)] == asset["dimensions"], "PNG dimensions do not match the declaration")
    elif kind == "svg":
        node = ElementTree.fromstring(data)
        need(node.tag == "{http://www.w3.org/2000/svg}svg", "asset is not namespaced SVG")
        box = [float(t) for t in re.split(r"[\s,]+", node.get("viewBox", "").strip()) if t]
        need(len(box) == 4 and all(map(math.isfinite, box)) and min(box[2:]) > 0,
             "missing or invalid SVG viewBox")
    else:
        raise GateError(f"unhandled icon format {kind!r}")


class Gate:
    def __init__(self, root, policy):
        p = Path(root)
        need(p.is_dir() and not p.is_symlink(), "expected a real final generated asset directory")
        self.root = p.resolve()
        self.policy = policy
        self.by_href = {v["link"]["href"]: k for k, v in policy["assets"].items()}
        self.rels = {v["link"]["rel"] for v in policy["assets"].values()} | set(policy["unsupported_rels"])
        self.checked_assets = set()

    def read(self, name):
        current = self.root
        for part in relative(name).parts:
            current = current / part
            need(not current.is_symlink(), f"symlink is not an approved output: {name}")
        need(current.is_file(), f"missing generated file: {name}")
        return current.read_bytes()

    def asset(self, key):
        if key not in self.checked_assets:
            a = self.policy["assets"][key]
            name = safe_href(a["link"]["href"])
            data = self.read(name)
            need(stamp(data) == binding(a), f"asset bytes/size drift: /{name}")
            inspect_format(data, a)
            self.checked_assets.add(key)

    def page(self, name):
        data = self.read(name)
        old = self.policy["historical_exceptions"].get(name)
        if old:
            need(stamp(data) == binding(old), "frozen HTML hash mismatch; policy normalization is not allowed")
        links = FaviconHead(data, self.rels).links
        if old:
            need(links == old["observed_links"], "historical favicon metadata provenance mismatch")
            for link in links:
                self.asset(self.by_href[link["href"]])
            for dep, record in old["protected_dependencies"].items():
                need(stamp(self.read(dep)) == binding(record), f"frozen dependency changed: {dep}")
            return "PASS_FROZEN_EXACT"
        seen = []
        for link in links:
            rel = link["rel"]
            need(not set(rel.lower().split()).intersection(self.policy["unsupported_rels"]),
                 f"unsupported favicon-related rel: {rel!r}")
            href = link.get("href", "")
            safe_href(href)
            key = self.by_href.get(href)
            need(key is not None, f"unapproved favicon URL: {href}")
            expected = self.policy["assets"][key]["link"]
            differences = sorted(k for k in link.keys() | expected.keys() if link.get(k) != expected.get(k))
            need(not differences, f"{href} unexpected attribute(s): {', '.join(differences)}; expected {expected}")
            seen.append(key)
        required = self.policy["required_order"]
        order = required + [x for x in self.policy["optional_order"] if x in seen]
        need(seen == order, f"wrong, duplicated or incomplete favicon sequence: {seen}; expected {order}")
        for key in seen:
            self.asset(key)
        return "PASS_PROFILE"

    def html_inventory(self):
        found = set()
        def cannot_read(error):
            raise error
        for dirpath, dirs, files in os.walk(self.root, onerror=cannot_read, followlinks=False):
            base = Path(dirpath)
            for name in dirs + files:
                need(not (base / name).is_symlink(), f"symlink in final generated tree: {(base / name).relative_to(self.root)}")
            for name in files:
                rel = (base / name).relative_to(self.root).as_posix()
                if Path(name).suffix.lower() in HTML_SUFFIXES:
                    found.add(rel)
        return found

    def release_scope(self, baseline_file, expected_sha):
        raw = Path(baseline_file).read_bytes()
        need(HASH.fullmatch(expected_sha) and sha256(raw).hexdigest() == expected_sha,
             "previous generated inventory digest differs from trusted pin")
        previous = json.loads(raw)["generated"]
        need(type(previous) is dict and previous, "missing/nonempty previous generated inventory required")
        for path, x in previous.items():
            relative(path)
            binding(x)
        exceptions = self.policy["historical_exceptions"]
        for path, x in exceptions.items():
            need(path in previous and binding(previous[path]) == binding(x),
                 f"historical path is not established by this baseline: {path}")
        prior_html = {p for p in previous if PurePosixPath(p).suffix.lower() in HTML_SUFFIXES}
        emitted = self.html_inventory()
        missing = prior_html - emitted
        need(not missing, f"HTML removal is not authorized by this prototype: {', '.join(sorted(missing))}")
        # Derived from output bytes, not a caller-supplied page list.
        scope = {p for p in emitted if p not in previous or stamp(self.read(p)) != binding(previous[p])}
        return sorted(scope | set(exceptions)), len(scope), len(emitted)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    render = sub.add_parser("render"); render.add_argument("--include", action="append", default=[])
    check = sub.add_parser("check", help="explicit paths for the private demo, not a release")
    check.add_argument("--root", required=True); check.add_argument("paths", nargs="+")
    release = sub.add_parser("release", help="automatically discover changed/added HTML and check all registered historical files")
    release.add_argument("--root", required=True)
    release.add_argument("--baseline-inventory", required=True)
    release.add_argument("--baseline-sha256", required=True)
    args = parser.parse_args()
    try:
        policy = load_policy()
        if args.mode == "render":
            print(render_favicon_links(policy, args.include))
            return 0
        gate = Gate(args.root, policy)
        if args.mode == "check":
            paths = args.paths
        else:
            for key in policy["required_order"]:
                gate.asset(key)
            paths, scope, total = gate.release_scope(args.baseline_inventory, args.baseline_sha256)
            print(f"Scope: {scope} added/changed HTML of {total}; plus registered historical paths")
        failures = 0
        for path in paths:
            try:
                print(f"{gate.page(path)} {path}")
            except (GateError, OSError, ElementTree.ParseError, ValueError) as e:
                failures += 1
                print(f"FAIL {path}: {e}", file=sys.stderr)
        return 1 if failures else 0
    except (OSError, GateError, KeyError, TypeError, ValueError, ElementTree.ParseError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
