"""Shared automatic pipeline loop for all data sources.

Owns the per-item loop, empty-data guards, and per-problem fan-out.
Source-specific behaviour is injected via a SourceAdapter frozen dataclass
— see the class docstring for the contract each field must satisfy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.llm.extractInsights import extract_insights
from app.utilities.getDate import getCurrentDate


@dataclass(frozen=True)
class SourceAdapter:
    """Per-source seams injected into run_automatic_pipeline.

    Fields
    ------
    item_id       : item -> identifier used for DB look-up and logging
    check_existing: id -> existing rows (truthy) or empty/falsy if absent
    bump_date     : (id, today) -> update the persisted date; no return value
    ingest        : item -> list of raw comments / reviews
    clean         : (raw_list, keywords) -> list of cleaned text strings
    system_prompt : per-source / per-category system prompt string
    output_prompt : per-source output-shape reminder string
    build_row     : (item, problem, today, data) -> single trend-data dict
    persist_row   : rows_list -> write to the appropriate Supabase table
    post_extract  : optional (extraction, item) -> None; called after a
                    successful extract_insights before per-problem fan-out
    """

    item_id: Callable[[dict], Any]
    check_existing: Callable[[Any], list | dict | None]
    bump_date: Callable[[Any, str], None]
    ingest: Callable[[dict], list]
    clean: Callable[[list, list[str]], list]
    system_prompt: str | Callable[[dict], str]
    output_prompt: str
    build_row: Callable[[dict, dict, str, dict], dict]
    persist_row: Callable[[list[dict]], None]
    post_extract: Callable[[Any, dict], None] | None = None


def run_automatic_pipeline(
    items: list[dict],
    keywords: list[str],
    adapter: SourceAdapter,
) -> list[dict]:
    """Run the full automatic pipeline for a list of items.

    For each item:
    - Short-circuit if already persisted: bump its date and carry it forward.
    - Ingest → clean; skip if cleaned data is empty.
    - Extract insights via LLM; skip if None (no usable problems).
    - Fan out one row per problem: build → persist → collect.

    Returns a list of all collected rows in processing order.
    """
    today = str(getCurrentDate())
    page_data = []

    for item in items:
        item_id = adapter.item_id(item)
        existing = adapter.check_existing(item_id)

        if existing:
            print(f"Skipped key: {item_id}. Found in Database.")
            adapter.bump_date(item_id, today)
            page_data.append(existing)
            continue

        raw = adapter.ingest(item)
        cleaned = adapter.clean(raw, keywords)

        if not cleaned:
            print(f"Skipping key: {item_id} due to empty cleaned data.")
            continue

        prompt = adapter.system_prompt(item) if callable(adapter.system_prompt) else adapter.system_prompt
        result = extract_insights(cleaned, prompt, adapter.output_prompt)

        if result is None:
            print(f"Skipping key: {item_id} due to no problems found.")
            continue

        if adapter.post_extract is not None:
            adapter.post_extract(result, item)

        for problem in result.problems:
            row = [adapter.build_row(item, problem, today, result)]
            adapter.persist_row(row)
            page_data.append(row)

    return page_data
