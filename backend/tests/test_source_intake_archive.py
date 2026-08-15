import io
import zipfile

import pytest

from backend.app.storage.archive import ArchiveSafetyError, ArchivePolicy, BoundedZipReader


def make_zip(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in entries:
            if name.endswith("/"):
                archive.writestr(name, b"")
            else:
                archive.writestr(name, content)
    return stream.getvalue()


def test_reader_preserves_unicode_spaces_and_empty_folder_without_extraction():
    reader = BoundedZipReader(make_zip([("FORME/Arabic name / نموذج.pdf", b"pdf"), ("FORME/EMPTY/", b"")]))
    observations = reader.observations_with_hashes()
    assert [item.normalized_safe_path for item in observations] == ["FORME/Arabic name / نموذج.pdf", "FORME/EMPTY"]
    assert observations[0].sha256
    assert observations[1].is_dir


@pytest.mark.parametrize("name", ["../escape.txt", "/absolute.txt", "\\\\server\\share\\x.txt", "C:/drive.txt", "a/../../escape.txt"])
def test_reader_rejects_unsafe_paths(name):
    with pytest.raises(ArchiveSafetyError):
        BoundedZipReader(make_zip([(name, b"x")])).observations()


def test_reader_rejects_duplicate_case_collision_and_nested_archive():
    with pytest.raises(ArchiveSafetyError):
        BoundedZipReader(make_zip([("A.txt", b"1"), ("a.txt", b"2")])).observations()
    with pytest.raises(ArchiveSafetyError):
        BoundedZipReader(make_zip([("nested.zip", b"not expanded")])).observations()


def test_reader_enforces_entry_limit_before_reading():
    with pytest.raises(ArchiveSafetyError):
        BoundedZipReader(make_zip([("one.txt", b"1"), ("two.txt", b"2")]), ArchivePolicy(max_entries=1)).observations()
