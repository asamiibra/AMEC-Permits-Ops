# Fixture-Safety Repair

Seed and test code now resolve synthetic workspace, mock-system, document, workbook, and SOR roots through environment-configurable helpers. The test fixture creates an isolated temporary workspace and cleans it at exit. Existing canonical source documents are preserved rather than rewritten. The Playwright JSON report defaults to ignored `frontend/test-results`; the Construction screenshot defaults to the closure artifact directory.

The adapter resolves configured roots before comparing paths, avoiding macOS `/var` versus `/private/var` mismatches. The canonical workbook and source PDFs were restored to their entry content; generated runtime directories are created only in the isolated synthetic workspace.
