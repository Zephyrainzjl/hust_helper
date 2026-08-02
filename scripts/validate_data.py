#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src/hust_helper/tools/hust_eater/data"


def main() -> int:
    catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    entities = [json.loads(line) for line in (DATA / "entities.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    manifest = json.loads((DATA / "media/manifest.json").read_text(encoding="utf-8"))
    assert catalog["source_pdf_pages"] == 49
    assert catalog["counts"]["chapters"] == 5
    assert catalog["counts"]["sections"] == 32
    assert catalog["counts"]["entries"] == len(entities) == 144
    assert catalog["counts"]["images"] == len(manifest["items"]) == 98
    ids = [item["id"] for item in entities]
    assert len(ids) == len(set(ids))
    for page in range(1, 50):
        assert (DATA / f"pages/page_{page:03d}.json").is_file()
        assert (DATA / f"pages/page_{page:03d}.md").is_file()
    for item in manifest["items"]:
        path = DATA / item["file"]
        assert path.is_file(), path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == item["sha256"], item["id"]
    source_pdf = DATA / catalog["source_pdf"]
    assert source_pdf.is_file()
    integrity = json.loads((DATA / catalog["integrity_file"]).read_text(encoding="utf-8"))
    assert integrity["source_pdf"]["sha256"] == hashlib.sha256(source_pdf.read_bytes()).hexdigest()
    assert integrity["entities"]["records"] == len(entities)
    assert integrity["media"]["png_files"] == len(manifest["items"])
    print(json.dumps({"status": "ok", "counts": catalog["counts"], "source_sha256": integrity["source_pdf"]["sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
