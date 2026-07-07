from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


DEFAULT_FOLLOW_UP_LIMIT = 20
SOURCE_GAP_STATUSES = {"needs_adapter", "needs_manual_seed", "no_data", "future"}
SOURCE_NOTE_CITATION_PREFIX = "research_source_note:"

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
KIND_ORDER = {
    "ai_summary_question": 0,
    "source_review": 1,
    "seed_prep": 2,
    "source_gap": 3,
    "research_note": 4,
}


def build_research_follow_up_queue(
    *,
    notes: list[dict[str, object]] | None,
    information_sources_payload: dict[str, object] | None,
    generated_at: str | None = None,
    limit: int = DEFAULT_FOLLOW_UP_LIMIT,
    diagnostics: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    source_items = _source_items(information_sources_payload)
    sources_by_id = {str(item.get("id")): item for item in source_items if item.get("id")}
    notes_by_source_id = _notes_by_source_id(notes or [])

    items: list[dict[str, object]] = []
    for note in notes or []:
        if str(note.get("review_status") or "") == "archived":
            continue
        items.extend(_build_note_follow_up_items(note, sources_by_id=sources_by_id))

    for source_item in source_items:
        items.extend(_build_source_follow_up_items(source_item, notes_by_source_id=notes_by_source_id))

    sorted_items = sorted(items, key=_sort_key)
    bounded_limit = max(1, min(limit, 100))
    visible_items = sorted_items[:bounded_limit]

    queue_diagnostics = list(diagnostics or [])
    return {
        "status": "degraded" if queue_diagnostics else "ok",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "summary": _build_summary(sorted_items, returned=len(visible_items)),
        "items": visible_items,
        "diagnostics": queue_diagnostics,
        "safety": {
            "not_investment_advice": True,
            "citations_require_reviewed_citable_notes": True,
            "no_automated_trading": True,
        },
    }


def _build_note_follow_up_items(
    note: dict[str, object],
    *,
    sources_by_id: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    note_id = _string_value(note.get("id"))
    if not note_id:
        return items

    metadata = _metadata(note)
    source_id = _string_value(metadata.get("source_id"))
    source_item = sources_by_id.get(source_id or "")
    citation_policy, citation_id = _citation_boundary_for_note(note)
    completeness_status = _completeness_status(metadata)

    base_item = _note_base_item(
        note,
        metadata=metadata,
        source_item=source_item,
        citation_policy=citation_policy,
        citation_id=citation_id,
    )

    ai_follow_up = _string_value(note.get("ai_follow_up"))
    if ai_follow_up:
        items.append(
            {
                **base_item,
                "id": f"source_note_ai_follow_up:{note_id}",
                "kind": "ai_summary_question",
                "priority": "high" if citation_policy == "citable" else "medium",
                "title": _string_value(note.get("title")) or "Source notebook follow-up",
                "prompt": ai_follow_up,
                "next_action": (
                    "Use this as a future AI-summary question after checking whether the note is "
                    "reviewed, citable, and still within the citation boundary."
                ),
            }
        )

    review_status = _string_value(note.get("review_status"))
    if (
        source_id
        and (
            completeness_status != "complete"
            or review_status != "reviewed"
            or citation_policy != "citable"
        )
    ):
        items.append(
            {
                **base_item,
                "id": f"source_note_review:{note_id}",
                "kind": "source_review",
                "priority": "medium" if citation_policy == "citable" else "high",
                "title": _string_value(note.get("title")) or "Review source notebook entry",
                "prompt": "Complete source review before relying on this note as AI-ready evidence.",
                "next_action": _source_review_next_action(note, metadata),
                "missing_review_checks": _missing_review_checks(metadata),
            }
        )

    return items


def _build_source_follow_up_items(
    source_item: dict[str, object],
    *,
    notes_by_source_id: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    source_id = _string_value(source_item.get("id"))
    if not source_id:
        return items

    linked_notes = notes_by_source_id.get(source_id, [])
    seed_ready_notes = [
        note for note in linked_notes if _completeness_status(_metadata(note)) == "complete"
    ]
    base_item = _source_base_item(
        source_item,
        linked_note_count=len(linked_notes),
        seed_ready_note_count=len(seed_ready_notes),
    )
    status = _string_value(source_item.get("status"))
    seed_template = source_item.get("seed_template") if isinstance(source_item.get("seed_template"), dict) else None

    if seed_template is not None or status == "needs_manual_seed":
        items.append(
            {
                **base_item,
                "id": f"source_seed_prep:{source_id}",
                "kind": "seed_prep",
                "priority": "high" if status == "needs_manual_seed" else "medium",
                "title": _string_value(source_item.get("label")) or source_id,
                "prompt": _string_value(seed_template.get("description") if seed_template else None)
                or _string_value(source_item.get("collection_note"))
                or "Prepare reviewed seed evidence for this source.",
                "next_action": _string_value(source_item.get("next_action"))
                or "Prepare reviewed source and method metadata before import.",
            }
        )

    if status in SOURCE_GAP_STATUSES:
        items.append(
            {
                **base_item,
                "id": f"source_gap:{source_id}",
                "kind": "source_gap",
                "priority": "high" if status in {"needs_adapter", "needs_manual_seed"} else "medium",
                "title": _string_value(source_item.get("label")) or source_id,
                "prompt": _string_value(source_item.get("collection_note"))
                or _string_value(source_item.get("ai_usage"))
                or "This source still needs local evidence before it can support AI summaries.",
                "next_action": _string_value(source_item.get("next_action"))
                or "Collect or review source evidence before using this source in AI context.",
            }
        )

    return items


def _note_base_item(
    note: dict[str, object],
    *,
    metadata: dict[str, object],
    source_item: dict[str, object] | None,
    citation_policy: str,
    citation_id: str | None,
) -> dict[str, object]:
    source_id = _string_value(metadata.get("source_id"))
    item: dict[str, object] = {
        "citation_policy": citation_policy,
        "note_id": _string_value(note.get("id")),
        "note_title": _string_value(note.get("title")),
        "source_name": _string_value(note.get("source_name")),
        "source_type": _string_value(note.get("source_type")),
        "source_id": source_id,
        "source_label": _string_value(metadata.get("source_label"))
        or _string_value(source_item.get("label") if source_item else None),
        "source_category": _string_value(metadata.get("source_category"))
        or _string_value(source_item.get("category") if source_item else None),
        "source_status": _string_value(source_item.get("status") if source_item else None),
        "target_indicator_codes": _string_list(metadata.get("target_indicator_codes")),
        "component_role": _string_value(metadata.get("component_role")),
        "completeness_status": _completeness_status(metadata),
        "as_of": _string_value(note.get("as_of") or note.get("published_at")),
        "retrieved_at": _string_value(note.get("retrieved_at")),
    }
    if citation_id is not None:
        item["citation_id"] = citation_id
    return item


def _source_base_item(
    source_item: dict[str, object],
    *,
    linked_note_count: int,
    seed_ready_note_count: int,
) -> dict[str, object]:
    return {
        "citation_policy": "guidance_only",
        "source_id": _string_value(source_item.get("id")),
        "source_label": _string_value(source_item.get("label")),
        "source_category": _string_value(source_item.get("category")),
        "source_status": _string_value(source_item.get("status")),
        "target_indicator_codes": _target_indicator_codes_for_source(source_item),
        "source_name": _string_value(source_item.get("authority")),
        "source_type": "information_source",
        "as_of": _string_value(source_item.get("latest_as_of")),
        "linked_note_count": linked_note_count,
        "seed_ready_note_count": seed_ready_note_count,
        "citation_boundary": _string_value(source_item.get("citation_policy")),
    }


def _build_summary(items: list[dict[str, object]], *, returned: int) -> dict[str, int]:
    summary = {
        "total": len(items),
        "returned": returned,
        "source_review": 0,
        "seed_prep": 0,
        "ai_summary_question": 0,
        "source_gap": 0,
        "research_note": 0,
        "citable": 0,
        "collection_only": 0,
        "guidance_only": 0,
    }
    for item in items:
        kind = _string_value(item.get("kind"))
        if kind in summary:
            summary[kind] += 1
        policy = _string_value(item.get("citation_policy"))
        if policy in summary:
            summary[policy] += 1
    return summary


def _source_review_next_action(note: dict[str, object], metadata: dict[str, object]) -> str:
    if str(note.get("review_status") or "") != "reviewed":
        return "Review the source note, add date/method metadata, and mark it reviewed when ready."
    if not bool(note.get("is_citable")):
        return "Decide whether this reviewed note is safe to mark AI-citable after checking excerpt and provenance."
    missing = _missing_review_checks(metadata)
    if missing:
        return f"Fill missing review checklist items: {', '.join(missing)}."
    return "Recheck source review completeness before using this item in research workflows."


def _citation_boundary_for_note(note: dict[str, object]) -> tuple[str, str | None]:
    citation_id = _string_value(note.get("citation_id"))
    if (
        note.get("is_citable") is True
        and str(note.get("review_status") or "") == "reviewed"
        and citation_id
        and citation_id.startswith(SOURCE_NOTE_CITATION_PREFIX)
    ):
        return "citable", citation_id
    return "collection_only", None


def _missing_review_checks(metadata: dict[str, object]) -> list[str]:
    checklist = metadata.get("review_checklist")
    if not isinstance(checklist, dict):
        return []
    return sorted(str(key) for key, value in checklist.items() if value is not True)


def _completeness_status(metadata: dict[str, object]) -> str:
    completeness = metadata.get("completeness")
    if not isinstance(completeness, dict):
        return "missing"
    status = _string_value(completeness.get("status"))
    return status or "missing"


def _notes_by_source_id(notes: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for note in notes:
        source_id = _string_value(_metadata(note).get("source_id"))
        if source_id:
            grouped.setdefault(source_id, []).append(note)
    return grouped


def _source_items(payload: dict[str, object] | None) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _target_indicator_codes_for_source(source_item: dict[str, object]) -> list[str]:
    seed_template = source_item.get("seed_template")
    if isinstance(seed_template, dict):
        target_codes = _string_list(seed_template.get("target_indicator_codes"))
        if target_codes:
            return target_codes
    return _string_list(source_item.get("coverage"))


def _metadata(note: dict[str, object]) -> dict[str, object]:
    metadata = note.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _string_value(item))]


def _sort_key(item: dict[str, object]) -> tuple[int, int, str, str]:
    priority = _string_value(item.get("priority")) or "low"
    kind = _string_value(item.get("kind")) or "research_note"
    title = _string_value(item.get("title") or item.get("source_label") or item.get("note_title")) or ""
    item_id = _string_value(item.get("id")) or ""
    return (
        PRIORITY_ORDER.get(priority, 99),
        KIND_ORDER.get(kind, 99),
        title.lower(),
        item_id,
    )
