from types import SimpleNamespace

from backend.app.services.proposal_generation_summary import canonical_generation_summary


def revision(snapshot):
    return SimpleNamespace(snapshot=snapshot)


def base_snapshot(plan, *, mutation_count=0, owner_mutations=None):
    return {
        "source_set_hash": "manifest-current",
        "editor_document_version_id": "doc-current",
        "change_plan": plan,
        "generation_validation": {
            "state": "PASSED",
            "full_document_generation": "COMPLETE",
            "full_document_validation": "PASS",
            "coverage_state": "PASS",
        },
        "ai_provenance": {
            "generated_from_ai": True,
            "source_set_hash": "manifest-current",
            "provenance_state": "RECORDED",
            # This deliberately may disagree with the plan. The plan wins.
            "mutation_count": mutation_count,
        },
        "owner_mutations": owner_mutations or [],
    }


def test_summary_counts_only_published_plan_mutations():
    snapshot = base_snapshot({
        "mutations": [
            {"anchor": "a", "published_status": "PUBLISHED"},
            {"anchor": "b", "published": False},
        ]
    }, mutation_count=7)
    summary = canonical_generation_summary(revision(snapshot))
    assert summary["state"] == "READY_FOR_EDIT"
    assert summary["published_ai_mutation_count"] == 1
    assert [item["anchor"] for item in summary["published_mutations"]] == ["a"]


def test_zero_published_mutations_is_review_unless_explicit_no_change():
    review = canonical_generation_summary(revision(base_snapshot({"mutations": []}, mutation_count=7)))
    assert review["state"] == "GENERATION_REVIEW_REQUIRED"
    assert review["generation_review_reason"] == "AI_NO_DOCUMENT_MUTATIONS"
    no_change = canonical_generation_summary(revision(base_snapshot({"status": "NO_AI_CHANGES_REQUIRED", "mutations": []})))
    assert no_change["state"] == "NO_AI_CHANGES_REQUIRED"
    assert no_change["published_ai_mutation_count"] == 0


def test_owner_edits_are_separate_from_ai_mutations():
    summary = canonical_generation_summary(revision(base_snapshot(
        {"mutations": [{"anchor": "a"}]},
        mutation_count=1,
        owner_mutations=[{"anchor": "owner-a"}, {"anchor": "owner-b"}],
    )))
    assert summary["published_ai_mutation_count"] == 1
    assert summary["owner_mutation_count"] == 2
