#!/usr/bin/env python3
"""Find high-quality papers and add the top pick to a Zotero collection.

Zotero 9: the local API (/api/) is read-only. Writes use /connector/saveItems
and /connector/updateSession. Uses Python standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
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
    "collections": {"to_read": "From_codex"},
    "venues": {
        "conferences": [
            "ICRA", "IROS", "ICCV", "CVPR", "ECCV", "3DV", "RSS",
            "ICLR", "ICML", "NeurIPS", "IJCAI", "AAAI",
        ],
        "accept_ieee_transactions": True,
        "ccf_ab_journals": [
            "IEEE Transactions on Pattern Analysis and Machine Intelligence",
            "International Journal of Computer Vision",
            "IEEE Transactions on Robotics",
            "IEEE Transactions on Neural Networks and Learning Systems",
            "IEEE Transactions on Image Processing",
            "IEEE Transactions on Cybernetics",
            "IEEE Transactions on Multimedia",
            "Pattern Recognition",
            "IEEE Robotics and Automation Letters",
            "Journal of Field Robotics",
            "Autonomous Robots",
        ],
    },
    "search": {"max_candidates": 30, "top_n": 1},
}

CONFIG_PATH = str(Path.home() / ".zotero-codex" / "config.json")
USER_AGENT = "zotero-find-skill/1.0"


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


def http_request(url: str, method: str = "GET", body: dict | None = None, timeout: int = 25):
    data = None
    headers = {"User-Agent": USER_AGENT, "Zotero-API-Version": "3"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _opener(url).open(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)
    except urllib.error.URLError as e:
        return 0, str(e.reason), {}


def read_collections(cfg: dict) -> list:
    base = cfg["zotero"]["base_url"]
    _, body, _ = http_request(f"{base}/api/users/0/collections?format=json")
    try:
        return json.loads(body)
    except ValueError:
        return []


def read_items(cfg: dict, limit: int = 50) -> list:
    base = cfg["zotero"]["base_url"]
    q = urllib.parse.urlencode({
        "format": "json", "limit": limit, "sort": "dateAdded", "direction": "desc",
    })
    _, body, _ = http_request(f"{base}/api/users/0/items?{q}")
    try:
        items = json.loads(body)
    except ValueError:
        return []
    out = []
    for it in items:
        d = it.get("data", {})
        if d.get("itemType") in ("attachment", "note"):
            continue
        out.append(it)
    return out


def collection_ids(cfg: dict, name: str) -> tuple[str | None, str | None]:
    """Return (collection key from API, numeric collectionID from sqlite)."""
    key = None
    for c in read_collections(cfg):
        if c.get("data", {}).get("name") == name:
            key = c.get("key")
            break
    num = None
    db = Path(cfg["zotero"]["data_dir"]) / "zotero.sqlite"
    if db.exists() and key:
        try:
            conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro&immutable=1", uri=True)
            try:
                row = conn.execute(
                    "SELECT collectionID FROM collections WHERE key=?", (key,)
                ).fetchone()
                if row:
                    num = str(row[0])
            finally:
                conn.close()
        except sqlite3.Error:
            pass
    return key, num


def search_semantic_scholar(query: str, limit: int) -> list:
    fields = "title,abstract,year,venue,citationCount,externalIds,authors,publicationVenue"
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode({
        "query": query, "limit": limit, "fields": fields,
    })
    for attempt in range(3):
        status, body, _ = http_request(url)
        if status == 200:
            break
        if status == 429 and attempt < 2:
            time.sleep(3 * (attempt + 1))
            continue
        print(f"WARN: Semantic Scholar HTTP {status}: {body[:160]}", file=sys.stderr)
        return []
    try:
        data = json.loads(body)
    except ValueError:
        return []
    out = []
    for p in data.get("data", []):
        pv = p.get("publicationVenue") or {}
        venue = p.get("venue") or pv.get("name") or ""
        out.append({
            "source": "semanticscholar",
            "title": p.get("title") or "",
            "abstract": p.get("abstract") or "",
            "year": p.get("year"),
            "venue": venue,
            "journal": venue,
            "citationCount": p.get("citationCount") or 0,
            "externalIds": p.get("externalIds") or {},
            "authors": [{"name": (a.get("name") or "").strip()} for a in (p.get("authors") or [])],
        })
    return out


def search_crossref(query: str, limit: int) -> list:
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query.bibliographic": query,
        "rows": limit,
        "select": "DOI,title,container-title,issued,author,type",
        "mailto": "research@example.com",
    })
    status, body, _ = http_request(url)
    if status != 200:
        return []
    try:
        items = json.loads(body)["message"]["items"]
    except (ValueError, KeyError):
        return []
    out = []
    for it in items:
        title = (it.get("title") or [""])[0]
        container = it.get("container-title") or [""]
        journal = container[0] if container else ""
        year = None
        issued = it.get("issued", {}).get("date-parts", [[None]])
        if issued and issued[0]:
            year = issued[0][0]
        authors = []
        for a in it.get("author", []):
            name = " ".join(x for x in [a.get("given", ""), a.get("family", "")] if x).strip()
            if name:
                authors.append({"name": name})
        out.append({
            "source": "crossref",
            "title": title,
            "abstract": "",
            "year": year,
            "venue": journal,
            "journal": journal,
            "citationCount": 0,
            "externalIds": {"DOI": it.get("DOI")},
            "authors": authors,
        })
    return out


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def venue_ok(cfg: dict, p: dict) -> bool:
    v = _norm(p.get("venue") or "")
    j = _norm(p.get("journal") or "")
    confs = [_norm(c) for c in cfg["venues"]["conferences"]]
    for c in confs:
        if c in v or c in j:
            return True
    if cfg["venues"].get("accept_ieee_transactions", True):
        if "ieee transactions" in v or "ieee trans." in v or "ieee transactions" in j or "ieee trans." in j:
            return True
    for name in cfg["venues"].get("ccf_ab_journals", []):
        if _norm(name) in v or _norm(name) in j:
            return True
    return False


def _score(cfg: dict, p: dict) -> float:
    s = 0.0
    try:
        s += math.log1p(int(p.get("citationCount") or 0)) * 8
    except (TypeError, ValueError):
        pass
    if p.get("year"):
        try:
            s += max(0, int(p["year"]) - 2015) * 0.5
        except (TypeError, ValueError):
            pass
    v = _norm(p.get("venue") or "")
    if any(_norm(c) in v for c in cfg["venues"]["conferences"]):
        s += 5
    if "ieee transactions" in v:
        s += 5
    return s


def _dedupe(papers: list) -> list:
    seen = set()
    out = []
    for p in papers:
        doi = (p.get("externalIds") or {}).get("DOI")
        key = (doi or "").lower() or _norm(p.get("title") or "")[:80]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _build_item(cfg: dict, p: dict, query: str) -> dict:
    v = _norm(p.get("venue") or "")
    is_journal = any(tok in v for tok in ("journal", "transactions", "letters", "review")) or \
        any(_norm(n) in v for n in cfg["venues"]["ccf_ab_journals"])
    item = {
        "itemType": "journalArticle" if is_journal else "conferencePaper",
        "title": p.get("title") or "",
        "date": str(p["year"]) if p.get("year") else "",
        "DOI": (p.get("externalIds") or {}).get("DOI") or "",
        "abstractNote": (p.get("abstract") or "")[:8000],
        "tags": [{"tag": "from_codex"}],
        "notes": [{"note": f"Added by zotero-find. Query: {query}\nVenue: {p.get('venue') or ''}"}],
    }
    if is_journal:
        item["publicationTitle"] = p.get("venue") or ""
    else:
        item["conferenceName"] = p.get("venue") or ""
    creators = []
    for a in (p.get("authors") or [])[:20]:
        name = (a.get("name") or "").strip()
        if not name:
            continue
        parts = name.rsplit(" ", 1)
        first = parts[0] if len(parts) == 2 else ""
        last = parts[1] if len(parts) == 2 else name
        creators.append({"firstName": first, "lastName": last, "creatorType": "author"})
    item["creators"] = creators
    return item


def add_paper(cfg: dict, p: dict, query: str, dry_run: bool) -> None:
    base = cfg["zotero"]["base_url"]
    name = cfg["collections"]["to_read"]
    key, num = collection_ids(cfg, name)
    if not key:
        print(f"WARN: collection '{name}' not found. Create it in Zotero first; saving to library without collection target.")
    item = _build_item(cfg, p, query)
    doi = (p.get("externalIds") or {}).get("DOI")
    uri = f"https://doi.org/{doi}" if doi else "https://zotero.org"
    session_id = str(uuid.uuid4())
    save_body = {"sessionID": session_id, "items": [item], "uri": uri}
    move_body = {"sessionID": session_id, "target": f"C{num}"} if num else None
    if dry_run:
        print(json.dumps({"saveItems": save_body, "updateSession": move_body}, ensure_ascii=False, indent=2))
        return
    status, body, _ = http_request(f"{base}/connector/saveItems", method="POST", body=save_body)
    print(f"saveItems -> HTTP {status}: {body[:400]}")
    if move_body:
        status2, body2, _ = http_request(f"{base}/connector/updateSession", method="POST", body=move_body)
        print(f"updateSession -> HTTP {status2}: {body2[:400]}")


def cmd_infer(cfg: dict) -> None:
    print("COLLECTIONS:")
    for c in read_collections(cfg):
        d = c.get("data", {})
        print(f"  - {d.get('name')} (items={c.get('meta', {}).get('numItems')})")
    tags = {}
    print("RECENT TOP-LEVEL ITEMS:")
    for it in read_items(cfg, limit=40):
        d = it.get("data", {})
        print(f"  - [{d.get('date') or ''}] {d.get('title') or ''} | {d.get('publicationTitle') or d.get('conferenceName') or ''}")
        for t in d.get("tags", []):
            tag = t.get("tag")
            if tag:
                tags[tag] = tags.get(tag, 0) + 1
    if tags:
        print("TAG FREQUENCY:")
        for tag, n in sorted(tags.items(), key=lambda x: -x[1]):
            print(f"  - {tag}: {n}")


def cmd_search(cfg: dict, query: str, top_n: int, dry_run: bool) -> None:
    limit = cfg["search"]["max_candidates"]
    papers = _dedupe(search_semantic_scholar(query, limit) + search_crossref(query, limit))
    papers = [p for p in papers if venue_ok(cfg, p)]
    papers.sort(key=lambda p: _score(cfg, p), reverse=True)
    if not papers:
        print("NO_CANDIDATES_PASSING_VENUE_FILTER")
        print("HINT: try a more specific query, or widen the venue list in config.json if intended.")
        return
    for i, p in enumerate(papers[:top_n]):
        doi = (p.get("externalIds") or {}).get("DOI") or "-"
        print(f"[{i+1}] {p.get('title')}")
        print(f"    venue={p.get('venue') or '-'}  year={p.get('year') or '-'}  cites={p.get('citationCount')}  doi={doi}")
    winner = papers[0]
    add_paper(cfg, winner, query, dry_run)


def _resolve_doi(doi: str) -> dict:
    status, body, _ = http_request(
        "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    )
    if status == 200:
        try:
            it = json.loads(body)["message"]
            title = (it.get("title") or [""])[0]
            container = it.get("container-title") or [""]
            journal = container[0] if container else ""
            year = None
            issued = it.get("issued", {}).get("date-parts", [[None]])
            if issued and issued[0]:
                year = issued[0][0]
            authors = []
            for a in it.get("author", []):
                name = " ".join(x for x in [a.get("given", ""), a.get("family", "")] if x).strip()
                if name:
                    authors.append({"name": name})
            return {
                "title": title, "abstract": it.get("abstract") or "", "year": year,
                "venue": journal, "journal": journal, "citationCount": 0,
                "externalIds": {"DOI": doi}, "authors": authors,
            }
        except (ValueError, KeyError):
            pass
    return {}


def cmd_add(cfg: dict, doi: str, dry_run: bool) -> None:
    p = _resolve_doi(doi)
    if not p.get("title"):
        print("COULD_NOT_RESOLVE_DOI")
        return
    print(f"Resolved: {p['title']} | {p.get('venue')}")
    add_paper(cfg, p, f"manual doi:{doi}", dry_run)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="zotero-find")
    ap.add_argument("--config", default=None)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("infer")
    sp = sub.add_parser("search")
    sp.add_argument("--query", required=True)
    sp.add_argument("--top", type=int, default=None)
    sp.add_argument("--dry-run", action="store_true")
    ap_add = sub.add_parser("add")
    ap_add.add_argument("--doi", required=True)
    ap_add.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.command == "infer":
        cmd_infer(cfg)
    elif args.command == "search":
        top = args.top or cfg["search"]["top_n"]
        cmd_search(cfg, args.query, top, args.dry_run)
    elif args.command == "add":
        cmd_add(cfg, args.doi, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
