from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
import threading
import uuid
from importlib.resources import as_file
from pathlib import Path
from typing import Any, Iterable

from hust_helper.config import settings

from .models import FoodEntry
from .paths import data_resource


class HustEaterRepository:
    """Merged view of immutable package data and non-destructive user overlays."""

    def __init__(self, user_data_dir: str | Path | None = None) -> None:
        self.user_data_dir = Path(user_data_dir) if user_data_dir else settings.resolved_data_dir()
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.overlay_path = self.user_data_dir / "hust_eater_overlay.json"
        self.user_media_dir = self.user_data_dir / "media"
        self.user_media_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._base_entries: dict[str, FoodEntry] | None = None
        self._base_manifest: dict[str, dict[str, Any]] | None = None

    def _load_base_entries(self) -> dict[str, FoodEntry]:
        if self._base_entries is None:
            records: dict[str, FoodEntry] = {}
            resource = data_resource("entities.jsonl")
            with resource.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        entry = FoodEntry.from_mapping(json.loads(line))
                        records[entry.id] = entry
            self._base_entries = records
        return self._base_entries

    def _load_base_manifest(self) -> dict[str, dict[str, Any]]:
        if self._base_manifest is None:
            resource = data_resource("media/manifest.json")
            with resource.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            self._base_manifest = {item["id"]: item for item in raw.get("items", [])}
        return self._base_manifest

    @staticmethod
    def _empty_overlay() -> dict[str, Any]:
        return {"schema_version": "1.0", "upserts": {}, "deleted_ids": [], "media": {}}

    def _read_overlay(self) -> dict[str, Any]:
        if not self.overlay_path.exists():
            return self._empty_overlay()
        try:
            data = json.loads(self.overlay_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"Cannot read overlay: {self.overlay_path}") from exc
        result = self._empty_overlay()
        result.update(data)
        result["upserts"] = dict(result.get("upserts", {}))
        result["deleted_ids"] = list(result.get("deleted_ids", []))
        result["media"] = dict(result.get("media", {}))
        return result

    def _write_overlay(self, overlay: dict[str, Any]) -> None:
        tmp = self.overlay_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(overlay, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.overlay_path)

    def list_entries(self, include_deleted: bool = False) -> list[FoodEntry]:
        with self._lock:
            merged = dict(self._load_base_entries())
            overlay = self._read_overlay()
            for key, value in overlay["upserts"].items():
                merged[key] = FoodEntry.from_mapping(value)
            if not include_deleted:
                for key in overlay["deleted_ids"]:
                    merged.pop(key, None)
            return sorted(
                merged.values(),
                key=lambda item: (
                    item.chapter_id,
                    item.section_id,
                    item.ordinal,
                    item.name,
                ),
            )

    def get(self, entry_id: str) -> FoodEntry:
        for entry in self.list_entries():
            if entry.id == entry_id:
                return entry
        raise KeyError(f"Food entry not found: {entry_id}")

    def add(self, entry: FoodEntry | dict[str, Any]) -> FoodEntry:
        with self._lock:
            value = entry if isinstance(entry, FoodEntry) else FoodEntry.from_mapping(entry)
            if not value.id:
                value.id = f"user-{uuid.uuid4().hex}"
            existing = {item.id for item in self.list_entries(include_deleted=True)}
            if value.id in existing:
                raise ValueError(f"Entry ID already exists: {value.id}")
            value.extensions = {**value.extensions, "origin": "user"}
            overlay = self._read_overlay()
            overlay["upserts"][value.id] = value.to_dict()
            overlay["deleted_ids"] = [x for x in overlay["deleted_ids"] if x != value.id]
            self._write_overlay(overlay)
            return value

    def update(self, entry_id: str, **changes: Any) -> FoodEntry:
        with self._lock:
            current = self.get(entry_id).to_dict()
            immutable = {"id"}
            invalid = immutable.intersection(changes)
            if invalid:
                raise ValueError(f"Cannot change fields: {sorted(invalid)}")
            for key, value in changes.items():
                if key not in FoodEntry.__dataclass_fields__:
                    current.setdefault("extensions", {})[key] = value
                else:
                    current[key] = value
            updated = FoodEntry.from_mapping(current)
            overlay = self._read_overlay()
            overlay["upserts"][entry_id] = updated.to_dict()
            overlay["deleted_ids"] = [x for x in overlay["deleted_ids"] if x != entry_id]
            self._write_overlay(overlay)
            return updated

    def delete(self, entry_id: str) -> None:
        with self._lock:
            _ = self.get(entry_id)
            overlay = self._read_overlay()
            if entry_id not in overlay["deleted_ids"]:
                overlay["deleted_ids"].append(entry_id)
            self._write_overlay(overlay)

    def restore(self, entry_id: str) -> FoodEntry:
        with self._lock:
            overlay = self._read_overlay()
            overlay["deleted_ids"] = [x for x in overlay["deleted_ids"] if x != entry_id]
            self._write_overlay(overlay)
            candidates = {item.id: item for item in self.list_entries(include_deleted=True)}
            if entry_id not in candidates:
                raise KeyError(entry_id)
            return candidates[entry_id]

    def reset_entry(self, entry_id: str) -> FoodEntry:
        """Discard a local upsert and expose the bundled version again."""
        with self._lock:
            overlay = self._read_overlay()
            overlay["upserts"].pop(entry_id, None)
            overlay["deleted_ids"] = [x for x in overlay["deleted_ids"] if x != entry_id]
            self._write_overlay(overlay)
            return self.get(entry_id)

    def reset_all(self) -> None:
        with self._lock:
            if self.overlay_path.exists():
                self.overlay_path.unlink()
            if self.user_media_dir.exists():
                shutil.rmtree(self.user_media_dir)
            self.user_media_dir.mkdir(parents=True, exist_ok=True)

    def catalog(self) -> dict[str, Any]:
        with data_resource("catalog.json").open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def page(self, page_number: int) -> dict[str, Any]:
        if not 1 <= page_number <= int(self.catalog()["source_pdf_pages"]):
            raise ValueError(f"Page out of range: {page_number}")
        resource = data_resource(f"pages/page_{page_number:03d}.json")
        with resource.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def page_markdown(self, page_number: int) -> str:
        resource = data_resource(f"pages/page_{page_number:03d}.md")
        return resource.read_text(encoding="utf-8")

    def media_record(self, media_id: str) -> dict[str, Any]:
        overlay = self._read_overlay()
        if media_id in overlay["media"]:
            return overlay["media"][media_id]
        manifest = self._load_base_manifest()
        if media_id not in manifest:
            raise KeyError(f"Media not found: {media_id}")
        return dict(manifest[media_id])

    def image_bytes(self, media_id: str) -> bytes:
        record = self.media_record(media_id)
        if record.get("source") == "user_overlay":
            path = self.user_data_dir / record["file"]
            return path.read_bytes()
        if record.get("source") == "base_override":
            return data_resource(record["base_file"]).read_bytes()
        return data_resource(record["file"]).read_bytes()

    def image_path(self, media_id: str) -> Path:
        """Return a usable file path; package resources may be temporarily materialized."""
        record = self.media_record(media_id)
        if record.get("source") == "user_overlay":
            return self.user_data_dir / record["file"]
        resource = data_resource(record.get("base_file", record["file"]))
        # Normal wheels are unpacked; `as_file` is retained for zip-import compatibility.
        with as_file(resource) as path:
            if path.exists():
                return Path(path)
        raise FileNotFoundError(media_id)

    def add_image(self, entry_id: str, source_path: str | Path, caption: str = "") -> str:
        with self._lock:
            source = Path(source_path)
            if not source.is_file():
                raise FileNotFoundError(source)
            entry = self.get(entry_id)
            media_id = f"user-media-{uuid.uuid4().hex}"
            suffix = source.suffix.lower() or ".bin"
            destination = self.user_media_dir / f"{media_id}{suffix}"
            shutil.copy2(source, destination)
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            mime, _ = mimetypes.guess_type(destination.name)
            overlay = self._read_overlay()
            overlay["media"][media_id] = {
                "id": media_id,
                "file": str(destination.relative_to(self.user_data_dir)).replace("\\", "/"),
                "caption": caption,
                "sha256": digest,
                "mime_type": mime or "application/octet-stream",
                "editable": True,
                "source": "user_overlay",
                "entry_id": entry_id,
            }
            media_ids = [*entry.media_ids, media_id]
            entry.extensions = {
                **entry.extensions,
                "user_media_ids": [
                    *entry.extensions.get("user_media_ids", []),
                    media_id,
                ],
            }
            entry.media_ids = media_ids
            overlay["upserts"][entry_id] = entry.to_dict()
            self._write_overlay(overlay)
            return media_id

    def update_image_caption(self, media_id: str, caption: str) -> dict[str, Any]:
        with self._lock:
            overlay = self._read_overlay()
            if media_id in overlay["media"]:
                record = dict(overlay["media"][media_id])
            else:
                base = self._load_base_manifest()
                if media_id not in base:
                    raise KeyError(f"Media not found: {media_id}")
                record = dict(base[media_id])
                record["base_file"] = record["file"]
                record["source"] = "base_override"
            record["caption"] = caption
            record["editable"] = True
            overlay["media"][media_id] = record
            self._write_overlay(overlay)
            return record

    def replace_image(self, media_id: str, source_path: str | Path, caption: str | None = None) -> dict[str, Any]:
        with self._lock:
            source = Path(source_path)
            if not source.is_file():
                raise FileNotFoundError(source)
            current = self.media_record(media_id)
            suffix = source.suffix.lower() or Path(current.get("file", "image.bin")).suffix or ".bin"
            destination = self.user_media_dir / f"{media_id}{suffix}"
            shutil.copy2(source, destination)
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            mime, _ = mimetypes.guess_type(destination.name)
            record = {
                **current,
                "id": media_id,
                "file": str(destination.relative_to(self.user_data_dir)).replace("\\", "/"),
                "caption": current.get("caption", "") if caption is None else caption,
                "sha256": digest,
                "mime_type": mime or "application/octet-stream",
                "editable": True,
                "source": "user_overlay",
            }
            record.pop("base_file", None)
            overlay = self._read_overlay()
            old = overlay["media"].get(media_id)
            if old and old.get("source") == "user_overlay":
                old_path = self.user_data_dir / old["file"]
                if old_path != destination:
                    old_path.unlink(missing_ok=True)
            overlay["media"][media_id] = record
            self._write_overlay(overlay)
            return record

    def remove_image(self, entry_id: str, media_id: str) -> FoodEntry:
        with self._lock:
            entry = self.get(entry_id)
            if media_id not in entry.media_ids:
                return entry
            entry.media_ids = [x for x in entry.media_ids if x != media_id]
            overlay = self._read_overlay()
            record = overlay["media"].pop(media_id, None)
            if record and record.get("source") == "user_overlay":
                path = self.user_data_dir / record["file"]
                path.unlink(missing_ok=True)
            overlay["upserts"][entry_id] = entry.to_dict()
            self._write_overlay(overlay)
            return entry

    def export(self, path: str | Path, format: str = "json") -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        entries = [entry.to_dict() for entry in self.list_entries()]
        if format == "jsonl":
            destination.write_text(
                "\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n",
                encoding="utf-8",
            )
        elif format == "json":
            destination.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            raise ValueError("format must be 'json' or 'jsonl'")
        return destination

    def iter_media(self, entry: FoodEntry) -> Iterable[dict[str, Any]]:
        for media_id in entry.media_ids:
            try:
                yield self.media_record(media_id)
            except KeyError:
                continue
