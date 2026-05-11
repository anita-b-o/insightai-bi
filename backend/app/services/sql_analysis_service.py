from __future__ import annotations

import re

from app.schemas.ai import SQLAnalysisResult

AGGREGATION_FUNCTION_PATTERN = re.compile(r"\b(sum|count|avg|min|max)\s*\(", re.IGNORECASE)
ORDER_BY_PATTERN = re.compile(r"\border\s+by\b", re.IGNORECASE)
GROUP_BY_PATTERN = re.compile(r"\bgroup\s+by\b", re.IGNORECASE)
LIMIT_PATTERN = re.compile(r"\blimit\s+\d+\b", re.IGNORECASE)
SELECT_PATTERN = re.compile(r"\bselect\b(?P<select>.*?)\bfrom\b", re.IGNORECASE | re.DOTALL)
GROUP_BY_CAPTURE_PATTERN = re.compile(
    r"\bgroup\s+by\b(?P<group_by>.*?)(?:\border\s+by\b|\blimit\b|$)",
    re.IGNORECASE | re.DOTALL,
)
AS_ALIAS_PATTERN = re.compile(r"\bas\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*$", re.IGNORECASE)


def _split_sql_list(value: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    depth = 0

    for character in value:
        if character == "(":
            depth += 1
        elif character == ")" and depth > 0:
            depth -= 1

        if character == "," and depth == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
            continue

        current.append(character)

    trailing = "".join(current).strip()
    if trailing:
        items.append(trailing)
    return items


def _normalize_identifier(expression: str) -> str:
    normalized = expression.strip().strip('"')
    alias_match = AS_ALIAS_PATTERN.search(normalized)
    if alias_match:
        return alias_match.group(1)

    if "." in normalized:
        normalized = normalized.split(".")[-1]
    return normalized.strip('"')


def analyze_sql(sql: str) -> SQLAnalysisResult:
    candidate = sql.strip().rstrip(";")
    aggregation_functions = [match.upper() for match in AGGREGATION_FUNCTION_PATTERN.findall(candidate)]
    select_match = SELECT_PATTERN.search(candidate)
    selected_columns = (
        [_normalize_identifier(item) for item in _split_sql_list(select_match.group("select"))]
        if select_match
        else []
    )

    group_by_match = GROUP_BY_CAPTURE_PATTERN.search(candidate)
    group_by_columns = (
        [_normalize_identifier(item) for item in _split_sql_list(group_by_match.group("group_by"))]
        if group_by_match
        else []
    )

    has_group_by = bool(group_by_columns)
    has_order_by = bool(ORDER_BY_PATTERN.search(candidate))
    has_limit = bool(LIMIT_PATTERN.search(candidate))

    return SQLAnalysisResult(
        is_aggregated=bool(aggregation_functions or has_group_by),
        aggregation_functions=aggregation_functions,
        group_by_columns=group_by_columns,
        selected_columns=selected_columns,
        has_group_by=has_group_by,
        has_order_by=has_order_by,
        has_limit=has_limit,
    )
