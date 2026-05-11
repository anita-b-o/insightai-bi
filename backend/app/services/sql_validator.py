from __future__ import annotations

import re

from fastapi import HTTPException, status

from app.models.dataset import Dataset

FORBIDDEN_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
    "merge",
    "call",
    "execute",
}

TABLE_REFERENCE_PATTERN = re.compile(r"\b(?:from|join)\s+([a-zA-Z0-9_\"\.]+)", re.IGNORECASE)
LIMIT_PATTERN = re.compile(r"\blimit\s+(\d+)\b", re.IGNORECASE)
WHERE_CLAUSE_PATTERN = re.compile(
    r"\bwhere\b(?P<where>.*?)(?:\border\s+by\b|\bgroup\s+by\b|\bhaving\b|\blimit\b|$)",
    re.IGNORECASE | re.DOTALL,
)
SQL_COMMENT_PATTERN = re.compile(r"(--|/\*)")
UNSAFE_WHERE_PATTERNS = (
    re.compile(r"\bor\s+1\s*=\s*1\b", re.IGNORECASE),
    re.compile(r"\bor\s+'1'\s*=\s*'1'\b", re.IGNORECASE),
    re.compile(r'\bor\s+"1"\s*=\s*"1"\b', re.IGNORECASE),
    re.compile(r"\b\d+\s*=\s*\d+\b", re.IGNORECASE),
    re.compile(r"\b([a-z_][a-z0-9_]*)\s*=\s*\1\b", re.IGNORECASE),
    re.compile(r"\btrue\s*=\s*true\b", re.IGNORECASE),
    re.compile(r"\bor\s+true\b", re.IGNORECASE),
)
FORBIDDEN_SQL_PATTERNS = (
    re.compile(r"\bunion\b", re.IGNORECASE),
    re.compile(r"\bpg_sleep\s*\(", re.IGNORECASE),
    re.compile(r"\binformation_schema\b", re.IGNORECASE),
    re.compile(r"\bpg_catalog\b", re.IGNORECASE),
)


def _validate_where_clause(sql: str) -> None:
    where_match = WHERE_CLAUSE_PATTERN.search(sql)
    if where_match is None:
        return

    where_clause = where_match.group("where").strip()
    if not where_clause:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WHERE clause cannot be empty",
        )

    for pattern in UNSAFE_WHERE_PATTERNS:
        if pattern.search(where_clause):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsafe WHERE condition detected in generated SQL",
            )


def validate_and_normalize_sql(sql: str, dataset: Dataset) -> str:
    candidate = sql.strip()
    if candidate.endswith(";"):
        candidate = candidate[:-1].strip()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated SQL is empty")
    if ";" in candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only a single SELECT statement is allowed",
        )
    if SQL_COMMENT_PATTERN.search(candidate):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SQL comments are not allowed",
        )
    if not candidate.lower().startswith("select "):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only SELECT statements are allowed")

    lowered = candidate.lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Forbidden SQL keyword detected: {keyword.upper()}",
            )
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if pattern.search(candidate):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Forbidden SQL construct detected",
            )

    table_name = (dataset.table_name or "").lower()
    referenced_tables = {
        reference.replace('"', "").split(".")[-1].lower()
        for reference in TABLE_REFERENCE_PATTERN.findall(candidate)
    }
    if not referenced_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SQL must reference the dataset table in a FROM clause",
        )
    if referenced_tables != {table_name}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SQL can only query the target dataset table",
        )

    _validate_where_clause(candidate)

    limit_match = LIMIT_PATTERN.search(candidate)
    if limit_match:
        requested_limit = int(limit_match.group(1))
        if requested_limit > 100:
            candidate = LIMIT_PATTERN.sub("LIMIT 100", candidate, count=1)
    else:
        candidate = f"{candidate} LIMIT 100"

    return candidate
