from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def package_root():
    return files("hust_helper.tools.hust_eater")


def data_resource(relative: str = ""):
    root = package_root().joinpath("data")
    return root.joinpath(relative) if relative else root


def schema_resource(relative: str):
    return package_root().joinpath("schema", relative)


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
