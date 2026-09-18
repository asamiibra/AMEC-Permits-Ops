"""Package-preservation/merge tests; these do not certify an editor or AI."""
import io
import zipfile
import pytest
from backend.app.services.proposal_document_package import (
    DocumentPackageError, TextMutation, apply_text_mutations, document_map,
    merge_text_mutations, package_parts,
)


def package(body='<w:p><w:r><w:t>Duration: 3 months</w:t></w:r></w:p><w:p><w:r><w:t>Company brief unchanged</w:t></w:r></w:p>'):
    parts = {
        '[Content_Types].xml': b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        '_rels/.rels': b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="officeDocument" Target="word/document.xml"/></Relationships>',
        'word/document.xml': ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>').encode(),
        'word/styles.xml': b'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
        'word/media/logo.png': b'opaque-original-image',
        'word/header1.xml': b'<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>AMEC</w:t></w:r></w:p></w:hdr>',
    }
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for name,data in parts.items(): z.writestr(name,data)
    return out.getvalue()


def mutation(content, text, replacement):
    block=next(b for b in document_map(content) if b.text==text)
    return TextMutation(block.anchor,block.xml_hash,replacement)


def test_noop_is_byte_identical():
    data=package()
    assert apply_text_mutations(data,[]) is data
    assert apply_text_mutations(data,[mutation(data,'Duration: 3 months','Duration: 3 months')]) is data


def test_minimal_diff_preserves_other_xml_bytes_and_package_parts():
    data=package()
    changed=apply_text_mutations(data,[mutation(data,'Duration: 3 months','Duration: 4 months')])
    before,after=package_parts(data),package_parts(changed)
    assert before.keys()==after.keys()
    assert after['word/document.xml']==before['word/document.xml'].replace(b'3 months',b'4 months')
    assert all(before[n]==after[n] for n in before if n!='word/document.xml')
    assert [b.anchor for b in document_map(data)]==[b.anchor for b in document_map(changed)]


def test_arabic_replacement_adds_minimal_paragraph_bidi_without_rebuilding_docx():
    data = package('<w:p><w:r><w:t>English placeholder</w:t></w:r></w:p>')
    changed = apply_text_mutations(data, [mutation(data, 'English placeholder', 'نطاق الخدمات')])
    document = package_parts(changed)['word/document.xml']
    assert b'<w:pPr><w:bidi/></w:pPr>' in document
    assert any(block.text == 'نطاق الخدمات' for block in document_map(changed))
    assert package_parts(changed)['word/media/logo.png'] == b'opaque-original-image'


def test_existing_word_bidi_properties_are_preserved_for_mixed_replacement():
    data = package('<w:p><w:pPr><w:bidi/></w:pPr><w:r><w:rPr><w:rtl/></w:rPr><w:t>نطاق الخدمات</w:t></w:r></w:p>')
    changed = apply_text_mutations(data, [mutation(data, 'نطاق الخدمات', 'Scope of Services - 521')])
    document = package_parts(changed)['word/document.xml']
    assert document.count(b'<w:bidi/>') == 1
    assert document.count(b'<w:rtl/>') == 1
    assert b'Scope of Services - 521' in document


def test_preserves_table_cell_runs_and_xml_escaping():
    data=package('<w:tbl><w:tr><w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>A&amp;B</w:t></w:r><w:r><w:t>C</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
    changed=apply_text_mutations(data,[mutation(data,'A&BC','D<EF')])
    assert any(b.text=='D<EF' for b in document_map(changed))
    assert b'<w:rPr><w:b/></w:rPr>' in package_parts(changed)['word/document.xml']


def test_owner_edit_survives_unrelated_update_and_conflict_is_not_overwritten():
    base=package()
    owner=apply_text_mutations(base,[mutation(base,'Company brief unchanged','Owner revised brief')])
    result=merge_text_mutations(base,owner,[mutation(base,'Duration: 3 months','Duration: 4 months'),mutation(base,'Company brief unchanged','AI proposed brief')])
    text=[b.text for b in document_map(result.content)]
    assert 'Owner revised brief' in text and 'Duration: 4 months' in text
    assert 'AI proposed brief' not in text
    assert len(result.conflicts)==1 and result.conflicts[0]['status']=='NEEDS_OWNER_REVIEW'
    assert package_parts(owner)['word/document.xml'].replace(b'3 months',b'4 months')==package_parts(result.content)['word/document.xml']


def test_owner_formatting_change_is_also_protected():
    base=package()
    parts=package_parts(base)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for n,d in parts.items():
            z.writestr(n,d.replace(b'<w:r><w:t>Duration',b'<w:r><w:rPr><w:b/></w:rPr><w:t>Duration') if n=='word/document.xml' else d)
    owner=out.getvalue()
    result=merge_text_mutations(base,owner,[mutation(base,'Duration: 3 months','Duration: 4 months')])
    assert result.content==owner and len(result.conflicts)==1


def test_stale_or_duplicate_anchor_fails_atomically():
    data=package(); m=mutation(data,'Duration: 3 months','Duration: 4 months')
    with pytest.raises(DocumentPackageError,match='PRECONDITION'):
        apply_text_mutations(data,[TextMutation(m.anchor,'0'*64,m.replacement)])
    with pytest.raises(DocumentPackageError,match='DUPLICATE_MUTATION'):
        apply_text_mutations(data,[m,m])


@pytest.mark.parametrize('bad',['../escape','/escape','word/../escape','word\\escape','word/file:stream'])
def test_package_traversal_rejected(bad):
    out=io.BytesIO(package())
    with zipfile.ZipFile(out,'a') as z: z.writestr(bad,b'x')
    with pytest.raises(DocumentPackageError,match='INVALID_PACKAGE_PATH'): package_parts(out.getvalue())


def test_entity_and_missing_relationship_rejected():
    for old,new,code in [
        (b'<w:document',b'<!DOCTYPE x [<!ENTITY a "test">]><w:document','UNSAFE_XML'),
        (b'Target="word/document.xml"',b'Target="word/missing.xml"','UNRESOLVED_PACKAGE_RELATIONSHIP'),
    ]:
        parts=package_parts(package()); out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            for n,d in parts.items(): z.writestr(n,d.replace(old,new))
        with pytest.raises(DocumentPackageError,match=code): package_parts(out.getvalue())


def test_nested_textbox_paragraphs_are_independently_mapped_and_parent_is_not_rebuilt():
    data=package('<w:p><w:r><w:t>Outer</w:t><w:pict><w:txbxContent><w:p><w:r><w:t>Inner</w:t></w:r></w:p></w:txbxContent></w:pict></w:r></w:p>')
    assert {b.text for b in document_map(data)} >= {'Outer','Inner'}
    with pytest.raises(DocumentPackageError,match='COMPLEX_BLOCK'):
        apply_text_mutations(data,[mutation(data,'Outer','Changed')])
    changed=apply_text_mutations(data,[mutation(data,'Inner','Child')])
    assert package_parts(changed)['word/document.xml']==package_parts(data)['word/document.xml'].replace(b'Inner',b'Child')


@pytest.mark.parametrize('replacement',[' Bad','Bad ','Line\nBreak','Control\x00'])
def test_unsupported_text_edits_fail_closed(replacement):
    data=package()
    with pytest.raises(DocumentPackageError):
        apply_text_mutations(data,[mutation(data,'Duration: 3 months',replacement)])


def test_owner_inserted_paragraph_blocks_positional_merge():
    base=package()
    owner=package('<w:p><w:r><w:t>New owner paragraph</w:t></w:r></w:p><w:p><w:r><w:t>Duration: 3 months</w:t></w:r></w:p><w:p><w:r><w:t>Company brief unchanged</w:t></w:r></w:p>')
    result=merge_text_mutations(base,owner,[mutation(base,'Duration: 3 months','Duration: 4 months')])
    assert result.content==owner and not result.applied
    assert result.conflicts[0]['reason']=='DOCUMENT_STRUCTURE_CHANGED'


def test_utf16_xml_rejected_instead_of_using_invalid_byte_offsets():
    parts=package_parts(package()); out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for n,d in parts.items():
            z.writestr(n,d.decode().encode('utf-16') if n=='word/document.xml' else d)
    with pytest.raises(DocumentPackageError,match='UNSUPPORTED_XML_ENCODING'):
        document_map(out.getvalue())
