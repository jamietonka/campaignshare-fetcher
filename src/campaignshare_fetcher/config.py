from __future__ import annotations
import tomllib
from dataclasses import dataclass
from typing import Any


@dataclass
class Source:
    name: str
    type: str
    options: dict[str, Any]


@dataclass
class Config:
    sources: list[Source]


def load_config(path: str) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("config must contain a non-empty [sources] array")

    sources: list[Source] = []
    for i, item in enumerate(raw_sources):
        if not isinstance(item, dict):
            raise ValueError(f"sources[{i}] must be a table")
        name = item.get("name")
        stype = item.get("type")
        if not isinstance(name, str) or not name:
            raise ValueError(f"sources[{i}].name must be a non-empty string")
        if not isinstance(stype, str) or not stype:
            raise ValueError(f"sources[{i}].type must be a non-empty string")
        options = {k: v for k, v in item.items() if k not in ("name", "type")}
        sources.append(Source(name=name, type=stype, options=options))
    return Config(sources=sources)
