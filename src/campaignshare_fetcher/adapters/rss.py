from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, Any

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def _http_get(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# -------- Normalizers --------
def _rss_text(parent: ET.Element, tag: str) -> str | None:
    el = parent.find(tag)
    return el.text.strip() if el is not None and el.text else None


def _norm_rss_item(item: ET.Element) -> Dict[str, Any]:
    title = _rss_text(item, "title") or ""
    link = _rss_text(item, "link") or ""
    guid = _rss_text(item, "guid") or link or title
    pub = _rss_text(item, "pubDate") or ""
    stable = guid or link or title or str(time.time())
    nid = hashlib.sha1(stable.encode("utf-8")).hexdigest()
    return {
        "id": nid,
        "title": title,
        "url": link,
        "summary": "",
        "created_at": pub,
        "tags": ["rss"],
    }


def _norm_atom_entry(entry: ET.Element) -> Dict[str, Any]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    # title
    t = entry.find("atom:title", ns)
    title = (t.text or "").strip() if t is not None and t.text else ""
    # link href (prefer rel=alternate)
    link = ""
    for ln in entry.findall("atom:link", ns):
        rel = ln.attrib.get("rel", "alternate")
        href = ln.attrib.get("href", "")
        if rel == "alternate" and href:
            link = href
            break
        if not link and href:
            link = href
    # id / updated / published
    id_el = entry.find("atom:id", ns)
    guid = (
        (id_el.text or "").strip()
        if id_el is not None and id_el.text
        else link or title
    )
    updated = entry.find("atom:updated", ns)
    published = entry.find("atom:published", ns)
    when = (
        (published.text if published is not None else "")
        or (updated.text if updated is not None else "")
    ).strip()
    stable = guid or link or title or str(time.time())
    nid = hashlib.sha1(stable.encode("utf-8")).hexdigest()
    return {
        "id": nid,
        "title": title,
        "url": link,
        "summary": "",
        "created_at": when,
        "tags": ["rss", "atom"],
    }


# -------- Parser that handles RSS and Atom --------
def parse_feed(xml_bytes: bytes) -> Iterable[Dict[str, Any]]:
    root = ET.fromstring(xml_bytes)

    # RSS 2.0
    items = root.findall("./channel/item")
    if items:
        for it in items:
            yield _norm_rss_item(it)
        return

    # Fallback RSS-ish
    items = root.findall(".//item")
    if items:
        for it in items:
            yield _norm_rss_item(it)
        return

    # Atom 1.0 (namespace-aware or wildcard)
    entries = root.findall(".//{http://www.w3.org/2005/Atom}entry") or root.findall(
        ".//{*}entry"
    )
    if entries:
        for en in entries:
            yield _norm_atom_entry(en)
        return

    return


def run(
    source_name: str, url: str, output_path: str, state_dir: str = "data/state"
) -> dict:
    # Load state
    state_p = Path(state_dir) / f"{source_name}.json"
    seen: set[str] = set()
    if state_p.exists():
        try:
            seen = set(json.loads(state_p.read_text()).get("seen_ids", []))
        except Exception:
            seen = set()

    # Fetch + parse
    try:
        xml = _http_get(url)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        return {"ok": False, "error": f"http error: {e}"}

    items = list(parse_feed(xml))
    new_items = [it for it in items if it["id"] not in seen]

    # Append JSONL
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with out_p.open("a", encoding="utf-8") as f:
        for it in new_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    # Update state
    state_p.parent.mkdir(parents=True, exist_ok=True)
    seen.update(it["id"] for it in new_items)
    state_p.write_text(json.dumps({"seen_ids": sorted(seen)}))

    return {"ok": True, "total": len(items), "new": len(new_items), "path": str(out_p)}
