from backend.app.config.settings import repo_root
from backend.app.fixtures.canonical import canonical_sor_root, canonical_workbook_path, synthetic_documents_root, synthetic_workspace_root


def test_seed_fixture_outputs_are_outside_repository_source_tree():
    repository = repo_root().resolve()
    workspace = synthetic_workspace_root().resolve()
    assert workspace != repository
    assert repository not in workspace.parents
    for generated_path in (canonical_sor_root(), canonical_workbook_path(), synthetic_documents_root()):
        resolved = generated_path.resolve()
        assert repository not in resolved.parents
