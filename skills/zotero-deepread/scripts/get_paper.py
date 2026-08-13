#!/usr/bin/env python3
"""Locate a paper in the local Zotero library and print its metadata + PDF path."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_CONFIG = {
    "zotero": {
        "base_url": "http://127.0.0.1:23119",
        "data_dir": "",
    },
    "obsidian": {
        "vault_dir": "",
        "literature_dir": "",
    },
}

CONFIG_PATH = str(Path.home() / ".zotero-codex" / "config.json")
USER_AGENT = "zotero-deepread-skill/1.0"


def load_config(path: str | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    p = Path(path or os.environ.get("ZOTERO_CODEX_CONFIG") or CONFIG_PATH)
    if p.exists():
        try:
            user = json.loads(p.read_text(encoding="utf-8"))
            _deep_update(cfg, user)
        except (OSError, ValueError):
            pass
    return cfg


def _deep_update(base: dict, update: dict) -> None:
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v


def _opener(url: str) -> urllib.request.OpenerDirector:
    host = urllib.parse.urlparse(url).hostname
    if host in ("127.0.0.1", "localhost", "::1"):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def http_request(url: str, timeout: int = 20):
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Zotero-API-Version": "3"}
    )
    try:
        with _opener(url).open(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return 0, str(e.reason)


def http_post_json(url: str, body: dict, timeout: int = 20):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with _opener(url).open(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return 0, str(e.reason)


def bbt_citationkeys(cfg: dict, keys: list[str]) -> dict:
    if not keys:
        return {}
    status, body = http_post_json(
        f"{cfg['zotero']['base_url']}/better-bibtex/json-rpc",
        {"jsonrpc": "2.0", "method": "item.citationkey", "params": [keys], "id": 1},
    )
    if status != 200:
        return {}
    try:
        return json.loads(body).get("result") or {}
    except ValueError:
        return {}


def get_file_location(url: str) -> str | None:
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirect(), urllib.request.ProxyHandler({}))
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Zotero-API-Version": "3"}
    )
    try:
        resp = opener.open(req, timeout=20)
        loc = resp.headers.get("Location")
        resp.close()
        return loc
    except urllib.error.HTTPError as e:
        return e.headers.get("Location")
    except urllib.error.URLError:
        return None


def file_url_to_path(loc: str) -> str | None:
    if not loc or not loc.startswith("file:///"):
        return None
    raw = loc[len("file:///"):]
    raw = urllib.parse.unquote(raw)
    if len(raw) >= 2 and raw[1] == ":":
        return raw.replace("/", "\\")
    return "\\\\" + raw.replace("/", "\\")


def _citekey(data: dict) -> str:
    extra = data.get("extra") or ""
    m = re.search(r"Citation Key:\s*([A-Za-z0-9_\-:]+)", extra)
    if m:
        return m.group(1)
    auth = ""
    for c in data.get("creators") or []:
        if c.get("creatorType") == "author":
            auth = (c.get("lastName") or c.get("name") or "").lower()
            break
    title = re.sub(r"[^a-z0-9 ]", " ", (data.get("title") or "").lower())
    words = [w for w in title.split() if w]
    short = "".join(w[:3] for w in words[:3])
    ym = re.search(r"(\d{4})", data.get("date") or "")
    year = ym.group(1) if ym else ""
    key = re.sub(r"[^a-z0-9]", "", f"{auth}{short}{year}")
    return key or "paper"


def _authors(data: dict) -> str:
    out = []
    for c in data.get("creators") or []:
        if c.get("creatorType") == "author":
            out.append(" ".join(x for x in [c.get("firstName"), c.get("lastName")] if x))
    return ", ".join(out)


def cmd_find(cfg: dict, query: str) -> None:
    base = cfg["zotero"]["base_url"]
    q = urllib.parse.urlencode({"q": query, "qmode": "everything", "format": "json", "limit": 30})
    status, body = http_request(f"{base}/api/users/0/items?{q}")
    if status != 200:
        print(f"ERROR HTTP {status}: {body[:200]}")
        return
    try:
        items = json.loads(body)
    except ValueError:
        print("ERROR: bad JSON")
        return
    keys = [
        it.get("key")
        for it in items
        if (it.get("data") or {}).get("itemType") not in ("attachment", "note")
    ]
    ck = bbt_citationkeys(cfg, keys)
    for it in items:
        d = it.get("data", {})
        if d.get("itemType") in ("attachment", "note"):
            continue
        key = it.get("key")
        citekey = ck.get(key) or _citekey(d)
        print(f"{key}  [{citekey}]  {d.get('title') or ''}  | {d.get('date') or ''}  | doi={d.get('DOI') or '-'}")


def cmd_locate(cfg: dict, key: str) -> None:
    base = cfg["zotero"]["base_url"]
    status, body = http_request(f"{base}/api/users/0/items/{key}?format=json")
    if status != 200:
        print(f"ERROR HTTP {status}: {body[:200]}")
        return
    try:
        item = json.loads(body)
    except ValueError:
        print("ERROR: bad JSON")
        return
    data = item.get("data", {})
    citekey = bbt_citationkeys(cfg, [key]).get(key) or _citekey(data)
    pdf_path = None
    status, body = http_request(f"{base}/api/users/0/items/{key}/children?format=json")
    children = json.loads(body) if status == 200 else []
    for ch in children:
        cd = ch.get("data", {})
        if cd.get("contentType") == "application/pdf":
            loc = get_file_location(f"{base}/api/users/0/items/{ch.get('key')}/file")
            pdf_path = file_url_to_path(loc) if loc else None
            if pdf_path:
                break
    result = {
        "key": key,
        "citekey": citekey,
        "title": data.get("title") or "",
        "date": data.get("date") or "",
        "doi": data.get("DOI") or "",
        "publication": data.get("publicationTitle") or data.get("conferenceName") or data.get("proceedingsTitle") or "",
        "authors": _authors(data),
        "abstract": (data.get("abstractNote") or "")[:2000],
        "pdf_path": pdf_path,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="zotero-deepread")
    ap.add_argument("--config", default=None)
    sub = ap.add_subparsers(dest="command", required=True)
    sf = sub.add_parser("find")
    sf.add_argument("--query", required=True)
    sl = sub.add_parser("locate")
    sl.add_argument("--key", required=True)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.command == "find":
        cmd_find(cfg, args.query)
    elif args.command == "locate":
        cmd_locate(cfg, args.key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
