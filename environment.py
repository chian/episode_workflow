"""Read workflow configuration from this checkout and the caller's environment."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Mapping

ENV_FILE = Path(__file__).resolve().parent / ".env"


def workflow_environment(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """An explicit mapping is isolated; shell values otherwise override .env."""

    if env is not None:
        return dict(env)
    values: dict[str, str] = {}
    if ENV_FILE.is_file():
        for number, raw in enumerate(ENV_FILE.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            name, separator, value = line.partition("=")
            name = name.strip()
            if not separator or not name.isidentifier():
                raise ValueError(f"Invalid .env assignment on line {number}")
            try:
                words = shlex.split(value, comments=True)
            except ValueError as exc:
                raise ValueError(f"Invalid .env value on line {number}") from exc
            values[name] = " ".join(words)
    values.update(os.environ)
    return values
