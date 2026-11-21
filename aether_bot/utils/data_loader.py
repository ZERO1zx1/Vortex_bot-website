"""`data/` хавтасны статик JSON-ыг унших туслах.

Service давхарга л эдгээрийг уншина; cog/UI шууд файл нээхгүй. `lru_cache`
нь нэг process дотор дахин дахин parse хийхээс сэргийлнэ.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import config

DATA_DIR = config.BASE_DIR / "data"


@lru_cache(maxsize=64)
def load_json(relative_path: str) -> Any:
    base = DATA_DIR.resolve()
    path = (DATA_DIR / relative_path).resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"data зам буруу байна: {relative_path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_list(relative_path: str) -> list[dict[str, Any]]:
    data = load_json(relative_path)
    if not isinstance(data, list):
        raise TypeError(f"{relative_path} нь JSON массив байх ёстой")
    return data


def load_dict(relative_path: str) -> dict[str, Any]:
    data = load_json(relative_path)
    if not isinstance(data, dict):
        raise TypeError(f"{relative_path} нь JSON объект байх ёстой")
    return data


def data_path(*parts: str) -> Path:
    return DATA_DIR.joinpath(*parts)
