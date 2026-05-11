import json

from app.models.dataset import Dataset
from app.services.openai_service import request_openai_text
from app.services.schema_profile_service import build_dataset_schema_profile


def _build_sql_generation_prompt(question: str, dataset: Dataset) -> tuple[str, str]:
    columns = build_dataset_schema_profile(dataset)
    system_prompt = (
        "You generate safe PostgreSQL SELECT queries for a single dataset table. "
        "Return raw SQL only. No markdown, no explanation. "
        "Use only the provided table name and provided sql_name column names. "
        "Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or multiple statements. "
        "Always keep the query scoped to one table. "
        "If you use WHERE, it must contain real column filters and must never contain tautologies. "
        "Use semantic_type, sample_value, and cardinality to choose the right grouping, filtering, and aggregation. "
        "Avoid pie-chart-style groupings on high-cardinality categorical fields unless the question explicitly requests it."
    )
    user_prompt = (
        f"Question: {question}\n"
        f"Table name: {dataset.table_name}\n"
        "Available columns:\n"
        f"{json.dumps(columns, ensure_ascii=True, indent=2)}"
    )
    return system_prompt, user_prompt


async def generate_sql(question: str, dataset: Dataset) -> str:
    system_prompt, user_prompt = _build_sql_generation_prompt(question=question, dataset=dataset)
    return await request_openai_text(
        system_prompt,
        user_prompt,
        error_prefix="OpenAI API request failed during SQL generation",
    )


def _build_sql_correction_prompt(
    *,
    question: str,
    dataset: Dataset,
    failed_sql: str,
    execution_error: str,
) -> tuple[str, str]:
    columns = build_dataset_schema_profile(dataset)
    system_prompt = (
        "You repair PostgreSQL SELECT queries for a single dataset table. "
        "Return raw SQL only. No markdown, no explanation. "
        "Use only the provided table name and sql_name column names. "
        "Keep the intent of the question and avoid unsafe SQL. "
        "Fix the exact execution or validation error that you receive. "
        "Use semantic_type, sample_value, and cardinality to choose better columns and aggregations."
    )
    user_prompt = (
        f"Question: {question}\n"
        f"Table name: {dataset.table_name}\n"
        f"Failed SQL: {failed_sql}\n"
        f"Execution error: {execution_error}\n"
        "Available columns:\n"
        f"{json.dumps(columns, ensure_ascii=True, indent=2)}"
    )
    return system_prompt, user_prompt


async def correct_sql(
    *,
    question: str,
    dataset: Dataset,
    failed_sql: str,
    execution_error: str,
) -> str:
    system_prompt, user_prompt = _build_sql_correction_prompt(
        question=question,
        dataset=dataset,
        failed_sql=failed_sql,
        execution_error=execution_error,
    )
    return await request_openai_text(
        system_prompt,
        user_prompt,
        error_prefix="OpenAI API request failed during SQL correction",
    )
