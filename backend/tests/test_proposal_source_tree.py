from pathlib import Path
import hashlib
import os
import pytest
from backend.app.storage.proposal_source_tree import MountedProposalSource, classify_project_folder, PILOT_FOLDER
from backend.app.storage.errors import StorageError
from backend.app.storage.external import SourceChangedDuringImport


@pytest.mark.parametrize('name,expected',[
 ('454 - Al Watan Center','PROPOSALS_V1_ACTIVE_PILOT'),('520 - New client','DRAFT_SOURCE_PROJECT'),
 ('900 - Future','DRAFT_SOURCE_PROJECT'),('520','DRAFT_SOURCE_PROJECT'),('519 - Not included',None),
 ('455 - Not included',None),('454 - Different',None),('text 520',None),('520bad',None),('-520 project',None),('۵۲۰ name',None),
])
def test_discovery_is_source_only_and_excludes_middle_range(name,expected):
    value=classify_project_folder(name)
    assert (value.discovery_class if value else None)==expected


def tree(tmp_path):
    root=tmp_path/'source'; root.mkdir(); pilot=root/PILOT_FOLDER; pilot.mkdir()
    for name in ['Client data','Client Documents AMEC-P-D-2026-Q-454 Al Watan Center','Email','pdf EL WATAN CENTRE','Photo','Project Information','Tender Document']:
        (pilot/name).mkdir()
    (pilot/'Tender Document'/'Exact Name.txt').write_bytes(b'Client evidence')
    (pilot/'Al Wattan center 28-9-2023.rar').write_bytes(b'Archive bytes never extracted')
    (root/'520 - Draft').mkdir(); (root/'519 - Excluded').mkdir()
    return root,pilot


def test_exact_hierarchy_and_download_hash_without_source_writes(tmp_path):
    root,pilot=tree(tmp_path)
    before={str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
    with MountedProposalSource(root) as source:
        assert {p.number for p in source.discover()}=={454,520}
        entries=source.inventory(PILOT_FOLDER)
        assert len(entries)==9
        assert any(e.name=='Client data' for e in entries)
        captured=source.capture(PILOT_FOLDER+'/Tender Document/Exact Name.txt')
        assert captured.sha256==hashlib.sha256(b'Client evidence').hexdigest()
        assert captured.content==b'Client evidence'
        assert source.capture(PILOT_FOLDER+'/Al Wattan center 28-9-2023.rar').content==b'Archive bytes never extracted'
        caps=source.capabilities()
        assert not caps.write_new and not caps.mkdir and not caps.safe_finalize
        for name in ['write_temporary','finalize','mkdirs','cleanup_temporary','remove','rename']:
            assert not hasattr(source,name)
    assert before=={str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('path',['../outside','/etc/passwd',PILOT_FOLDER+'/../file',PILOT_FOLDER+'//file',PILOT_FOLDER+'/./file','519 - Excluded/file',PILOT_FOLDER+'/x:stream',PILOT_FOLDER+'\\file'])
def test_capture_rejects_unbounded_paths(tmp_path,path):
    root,_=tree(tmp_path)
    with MountedProposalSource(root) as source,pytest.raises(StorageError): source.capture(path)


def test_symlink_files_and_directories_are_not_followed(tmp_path):
    root,pilot=tree(tmp_path); outside=tmp_path/'outside'; outside.mkdir(); (outside/'secret').write_bytes(b'not a source')
    (pilot/'escape').symlink_to(outside,target_is_directory=True)
    (pilot/'secret').symlink_to(outside/'secret')
    with MountedProposalSource(root) as source:
        with pytest.raises(StorageError): source.inventory(PILOT_FOLDER)
        with pytest.raises(OSError): source.capture(PILOT_FOLDER+'/escape/secret')
        with pytest.raises(OSError): source.capture(PILOT_FOLDER+'/secret')


def test_file_changes_mid_capture_retry_but_never_accept_mixed_bytes(tmp_path,monkeypatch):
    root,pilot=tree(tmp_path); file=pilot/'Tender Document'/'Exact Name.txt'; original=os.read; writes=[]
    def changing(fd,size):
        chunk=original(fd,size)
        if chunk and not writes:
            file.write_bytes(b'changed evidence'); writes.append(True)
        return chunk
    monkeypatch.setattr(os,'read',changing)
    with MountedProposalSource(root) as source:
        captured=source.capture(PILOT_FOLDER+'/Tender Document/Exact Name.txt')
        assert captured.content==b'changed evidence'
        assert captured.sha256==hashlib.sha256(captured.content).hexdigest()


def test_source_replaced_during_capture_is_detected(tmp_path,monkeypatch):
    root,pilot=tree(tmp_path); file=pilot/'Tender Document'/'Exact Name.txt'; original=os.read; count=[]
    def changing(fd,size):
        chunk=original(fd,size)
        if chunk and not count:
            replacement=file.with_suffix('.new'); replacement.write_bytes(b'Client evidence'); replacement.replace(file); count.append(1)
        return chunk
    monkeypatch.setattr(os,'read',changing)
    with MountedProposalSource(root) as source, pytest.raises(SourceChangedDuringImport):
        source.capture(PILOT_FOLDER+'/Tender Document/Exact Name.txt',attempts=1)


def test_limits_and_closed_adapter(tmp_path):
    root,_=tree(tmp_path)
    with MountedProposalSource(root,max_file_bytes=2) as source:
        with pytest.raises(StorageError): source.capture(PILOT_FOLDER+'/Tender Document/Exact Name.txt')
    with pytest.raises(StorageError): source.children()
    with MountedProposalSource(root,max_entries=2) as source:
        with pytest.raises(StorageError): source.inventory(PILOT_FOLDER)


def test_special_files_rejected_without_blocking(tmp_path):
    root,pilot=tree(tmp_path); os.mkfifo(pilot/'pipe')
    with MountedProposalSource(root) as source:
        with pytest.raises(StorageError): source.capture(PILOT_FOLDER+'/pipe')


def test_unicode_and_shell_characters_remain_literal(tmp_path):
    root,pilot=tree(tmp_path); name='Arabic تقرير $(touch malicious).txt'; (pilot/name).write_bytes(b'literal')
    with MountedProposalSource(root) as source:
        assert source.capture(PILOT_FOLDER+'/'+name).content==b'literal'
        assert any(e.name==name for e in source.children(PILOT_FOLDER))
    assert not (pilot/'malicious').exists()
