from packages.services.research_follow_up_queue import build_research_follow_up_queue


def test_research_follow_up_queue_preserves_source_note_citation_boundaries():
    queue = build_research_follow_up_queue(
        generated_at="2026-07-07T00:00:00+00:00",
        notes=[
            {
                "id": "note-1",
                "title": "Buffett GDP source",
                "source_name": "World Bank",
                "source_type": "valuation_component",
                "ai_follow_up": "Summarize how this source supports the Buffett Indicator.",
                "review_status": "reviewed",
                "is_citable": True,
                "citation_id": "research_source_note:note-1",
                "as_of": "2026-01-02",
                "retrieved_at": "2026-01-03T00:00:00+00:00",
                "metadata": {
                    "source_id": "buffett_manual_valuation_components",
                    "source_label": "Buffett Indicator manual valuation components",
                    "source_category": "valuation",
                    "target_indicator_codes": ["buffett_indicator_us"],
                    "component_role": "gdp",
                    "review_checklist": {
                        "source_identity": True,
                        "source_url_or_document": True,
                        "date_metadata": True,
                        "excerpt": True,
                        "methodology": True,
                        "targets": True,
                        "license_note": True,
                    },
                    "completeness": {"score": 7, "total": 7, "status": "complete"},
                },
            },
            {
                "id": "note-2",
                "title": "Draft source note",
                "source_name": "Manual notebook",
                "source_type": "macro_context",
                "ai_follow_up": "Check whether this draft source is useful.",
                "review_status": "draft",
                "is_citable": False,
                "citation_id": None,
                "retrieved_at": "2026-01-04T00:00:00+00:00",
                "metadata": {
                    "source_id": "fred_us_rates",
                    "source_label": "FRED US rates",
                    "source_category": "macro",
                    "target_indicator_codes": ["us_10y_yield"],
                    "review_checklist": {
                        "source_identity": True,
                        "source_url_or_document": False,
                        "date_metadata": False,
                        "excerpt": True,
                        "methodology": False,
                        "targets": True,
                        "license_note": False,
                    },
                    "completeness": {"score": 3, "total": 7, "status": "partial"},
                },
            },
        ],
        information_sources_payload={
            "items": [
                {
                    "id": "fred_us_rates",
                    "label": "FRED US rates",
                    "category": "macro",
                    "authority": "Federal Reserve Bank of St. Louis FRED",
                    "status": "needs_adapter",
                    "next_action": "Add an official-source adapter or reviewed seed import.",
                    "collection_note": "Collect DGS10 observations from FRED before seeding rates data.",
                    "citation_policy": "FRED links are collection guidance only.",
                    "coverage": ["DGS10", "us_10y_yield"],
                    "latest_as_of": None,
                    "seed_template": {
                        "label": "FRED rates seed template",
                        "description": "Prepare reviewed daily Treasury observations.",
                        "target_indicator_codes": ["us_10y_yield"],
                    },
                },
                {
                    "id": "buffett_manual_valuation_components",
                    "label": "Buffett Indicator manual valuation components",
                    "category": "valuation",
                    "authority": "Operator-reviewed public sources",
                    "status": "needs_manual_seed",
                    "next_action": "Seed Buffett Indicator observations with source notes.",
                    "collection_note": "Collect market-cap and GDP components.",
                    "citation_policy": "Ratios are citeable only after stored locally.",
                    "coverage": ["buffett_indicator_us"],
                    "latest_as_of": None,
                    "seed_template": None,
                },
            ]
        },
    )

    items_by_id = {item["id"]: item for item in queue["items"]}

    citable_follow_up = items_by_id["source_note_ai_follow_up:note-1"]
    assert citable_follow_up["citation_policy"] == "citable"
    assert citable_follow_up["citation_id"] == "research_source_note:note-1"
    assert citable_follow_up["target_indicator_codes"] == ["buffett_indicator_us"]

    draft_follow_up = items_by_id["source_note_ai_follow_up:note-2"]
    assert draft_follow_up["citation_policy"] == "collection_only"
    assert "citation_id" not in draft_follow_up

    source_review = items_by_id["source_note_review:note-2"]
    assert source_review["citation_policy"] == "collection_only"
    assert source_review["missing_review_checks"] == [
        "date_metadata",
        "license_note",
        "methodology",
        "source_url_or_document",
    ]

    assert items_by_id["source_seed_prep:fred_us_rates"]["citation_policy"] == "guidance_only"
    assert items_by_id["source_gap:fred_us_rates"]["citation_policy"] == "guidance_only"
    assert "citation_id" not in items_by_id["source_seed_prep:fred_us_rates"]
    assert "citation_id" not in items_by_id["source_gap:fred_us_rates"]
    assert queue["summary"]["ai_summary_question"] == 2
    assert queue["summary"]["source_review"] == 1
    assert queue["summary"]["seed_prep"] == 2
    assert queue["summary"]["source_gap"] == 2
    assert queue["summary"]["citable"] == 1
    assert queue["summary"]["collection_only"] == 2
    assert queue["summary"]["guidance_only"] == 4


def test_research_follow_up_queue_caps_items_but_counts_full_workload():
    queue = build_research_follow_up_queue(
        notes=[],
        information_sources_payload={
            "items": [
                {
                    "id": f"source-{index}",
                    "label": f"Source {index}",
                    "category": "macro",
                    "status": "needs_adapter",
                    "next_action": "Add adapter.",
                    "collection_note": "Collect source.",
                    "coverage": [],
                    "seed_template": None,
                }
                for index in range(5)
            ]
        },
        limit=2,
    )

    assert len(queue["items"]) == 2
    assert queue["summary"]["total"] == 5
    assert queue["summary"]["returned"] == 2
