from backend.app.services.proposal_source_workspace import projects, tree


def test_fixture_discovers_pilot_and_520_draft_only():
    rows = projects()
    assert {row["number"] for row in rows} >= {454, 520}
    assert next(row for row in rows if row["number"] == 454)["state"] == "ACTIVE_PILOT"
    assert next(row for row in rows if row["number"] == 520)["state"] == "DRAFT_SYNCED"


def test_pilot_tree_keeps_expected_exact_names_and_nested_paths():
    entries = tree(454)["entries"]
    names = {entry["name"] for entry in entries}
    assert {"Client data", "Email", "Photo", "Project Information", "Tender Document"} <= names
    assert any(entry["path"].endswith("/client.txt") for entry in entries)
    assert any(entry["path"].endswith("/AMEC-P-D-2026-Q-454.pdf") for entry in entries)


def test_file_ids_are_path_bound_and_not_raw_paths():
    entries = tree(454)["entries"]
    files = [entry for entry in entries if not entry["is_directory"]]
    assert files and all(len(entry["id"]) == 24 and "/" not in entry["id"] for entry in files)
