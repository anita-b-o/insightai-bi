from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any


def _stringify(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _format_fields(fields: Mapping[str, Any]) -> str:
    return " ".join(f"{key}={_stringify(value)}" for key, value in fields.items() if value is not None)


def log_event(logger: logging.Logger, level: int, event: str, /, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.log(level, "%s %s", event, _format_fields(payload))

