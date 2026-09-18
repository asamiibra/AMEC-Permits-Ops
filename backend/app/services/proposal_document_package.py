"""Lossless, bounded DOCX text mutation primitives for Proposal V1.

This is a package boundary, not a Proposal store or an AI provider. Callers
must authorize access, validate evidence and persist a new immutable revision.
No HTML/plain-text document reconstruction occurs. Unsupported structure edits
are deliberately outside this primitive's contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import posixpath
import re
from typing import Iterable
from urllib.parse import unquote, urlsplit
from xml.parsers import expat
import zipfile

WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
MAX_BYTES = 64 * 1024 * 1024
MAX_PARTS = 2048


class DocumentPackageError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class TextSpan:
    start: int
    end: int
    value: str


@dataclass(frozen=True)
class DocumentBlock:
    anchor: str
    part: str
    start: int
    end: int
    xml_hash: str
    text: str
    text_spans: tuple[TextSpan, ...]
    has_nested_paragraphs: bool
    heading_level: int | None = None
    heading_style: str | None = None


@dataclass(frozen=True)
class TextMutation:
    anchor: str
    expected_xml_hash: str
    replacement: str


@dataclass(frozen=True)
class MergeResult:
    content: bytes
    applied: tuple[str, ...]
    conflicts: tuple[dict[str, str], ...]


def _parse(data: bytes):
    # Expat does not retrieve external resources; explicitly reject all DTDs,
    # entities, processing instructions and unsupported encoding anyway.
    if len(data) > MAX_BYTES:
        raise DocumentPackageError("XML_SIZE_LIMIT")
    if b"\x00" in data or (re.match(rb"\s*<\?xml[^>]*encoding=[\"\'](?![Uu][Tt][Ff]-?8)", data)):
        raise DocumentPackageError("UNSUPPORTED_XML_ENCODING")
    parser = expat.ParserCreate(namespace_separator="}")
    def deny(*_):
        raise DocumentPackageError("UNSAFE_XML")
    parser.StartDoctypeDeclHandler = deny
    parser.EntityDeclHandler = deny
    parser.ExternalEntityRefHandler = deny
    parser.ProcessingInstructionHandler = deny
    return parser


def _safe_part(name: str) -> bool:
    return bool(name and not name.startswith("/") and "\\" not in name
                and not any(p in {"", ".", ".."} for p in name.split("/"))
                and not any(ord(c) < 32 for c in name) and ":" not in name)


def package_parts(content: bytes) -> dict[str, bytes]:
    if len(content) > MAX_BYTES:
        raise DocumentPackageError("PACKAGE_SIZE_LIMIT")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_PARTS or sum(i.file_size for i in entries) > MAX_BYTES:
                raise DocumentPackageError("PACKAGE_EXPANSION_LIMIT")
            names = [i.filename for i in entries]
            if len(names) != len(set(names)) or any(not _safe_part(n) for n in names):
                raise DocumentPackageError("INVALID_PACKAGE_PATH")
            if any(i.flag_bits & 1 for i in entries):
                raise DocumentPackageError("ENCRYPTED_PACKAGE")
            parts = {i.filename: archive.read(i) for i in entries}
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise DocumentPackageError("INVALID_DOCX_PACKAGE") from exc
    if not {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= parts.keys():
        raise DocumentPackageError("REQUIRED_PACKAGE_PART_MISSING")
    for name, data in parts.items():
        if name.endswith((".xml", ".rels")):
            parser = _parse(data)
            relations: list[dict] = []
            parser.StartElementHandler = lambda tag, attrs: relations.append(attrs) if tag == REL + "}Relationship" else None
            try:
                parser.Parse(data, True)
            except expat.ExpatError as exc:
                raise DocumentPackageError("INVALID_PACKAGE_XML") from exc
            if name.endswith(".rels"):
                ids = [r.get("Id") for r in relations]
                if len(ids) != len(set(ids)):
                    raise DocumentPackageError("DUPLICATE_RELATIONSHIP_ID")
                source_dir = "" if name == "_rels/.rels" else posixpath.dirname(posixpath.dirname(name))
                for relation in relations:
                    target = relation.get("Target", "")
                    if relation.get("TargetMode") == "External":
                        # No external target is fetched by this library.
                        continue
                    resolved = posixpath.normpath(posixpath.join(source_dir, unquote(urlsplit(target).path)))
                    if not _safe_part(resolved) or resolved not in parts:
                        raise DocumentPackageError("UNRESOLVED_PACKAGE_RELATIONSHIP")
    return parts


def _heading_metadata(xml: bytes, style_headings: dict[str, tuple[int | None, str | None]] | None = None) -> tuple[int | None, str | None]:
    """Read native Word heading/outline metadata without guessing bold text."""
    ppr = re.search(rb"<w:pPr\b[^>]*>(.*?)</w:pPr>", xml, re.S)
    if not ppr:
        return None, None
    props = ppr.group(1)
    style_match = re.search(rb"<w:pStyle\b[^>]*w:val=[\"']([^\"']+)", props)
    style = style_match.group(1).decode("utf-8", "ignore") if style_match else None
    outline_match = re.search(rb"<w:outlineLvl\b[^>]*w:val=[\"'](\d+)", props)
    level = int(outline_match.group(1)) + 1 if outline_match else None
    numbering = bool(re.search(rb"<w:numPr\b", props))
    style_info = style_headings.get(style, (None, None)) if style_headings and style else (None, None)
    if level is None:
        level = style_info[0]
    if level is None and style:
        # Word commonly emits a direct Heading1/Heading2 style reference even
        # when the package omits a styles.xml definition (as in minimal DOCX
        # fixtures and some generated documents).  This is still native Word
        # structure, so recognize the explicit style name without guessing
        # from visual formatting.
        heading_match = re.search(r"heading\s*([1-9])", style, re.I)
        if heading_match:
            level = int(heading_match.group(1))
    if style is None:
        style = style_info[1]
    if level is None and numbering:
        # Numbering is accepted only when the paragraph visibly begins with a
        # reliable hierarchical number. This avoids turning arbitrary bold
        # paragraphs into guessed sections.
        visible = re.sub(rb"<[^>]+>", b"", xml)
        number_match = re.match(rb"\s*\d+(?:[.]\d+)*[.)]?\s+", visible)
        if number_match:
            level = number_match.group(0).count(b".") + 1
    return level, style


def _part_blocks(part: str, data: bytes, style_headings: dict[str, tuple[int | None, str | None]] | None = None) -> list[DocumentBlock]:
    parser = _parse(data)
    stack: list[dict] = []
    paragraphs: list[dict] = []
    blocks: list[DocumentBlock] = []
    root_counts: dict[str, int] = {}

    def start(tag, attrs):
        if len(stack) >= 128:
            raise DocumentPackageError("XML_DEPTH_LIMIT")
        counts = stack[-1]["counts"] if stack else root_counts
        counts[tag] = counts.get(tag, 0) + 1
        # Expanded names, not XML prefix spellings, define stable paths.
        parent_path = stack[-1]["path"] if stack else ""
        path = f"{parent_path}/{tag}[{counts[tag]}]"
        begin = parser.CurrentByteIndex
        close = data.index(b">", begin) + 1
        frame = dict(tag=tag, path=path, start=begin, open_end=close,
                     empty=data[begin:close].rstrip().endswith(b"/>"), counts={}, text=[])
        if tag == WORD + "}p":
            if paragraphs:
                paragraphs[-1]["nested"] = True
            frame.update(spans=[], nested=False)
            paragraphs.append(frame)
        if tag == WORD + "}t" and paragraphs:
            frame["owner"] = paragraphs[-1]
        stack.append(frame)

    def chars(value):
        if stack and stack[-1]["tag"] == WORD + "}t":
            stack[-1]["text"].append(value)

    def end(tag):
        frame = stack.pop()
        close_start = parser.CurrentByteIndex
        end_offset = frame["open_end"] if frame["empty"] else data.index(b">", close_start) + 1
        if tag == WORD + "}t" and "owner" in frame:
            if frame["empty"]:
                # A self-closing w:t cannot be edited as an inner-text span.
                return
            frame["owner"]["spans"].append(TextSpan(frame["open_end"], close_start, "".join(frame["text"])))
        if tag == WORD + "}p":
            paragraphs.pop()
            spans = tuple(frame["spans"])
            anchor = f"{part}#{digest(frame['path'].encode())}"
            heading_level, heading_style = _heading_metadata(data[frame["start"]:end_offset], style_headings)
            blocks.append(DocumentBlock(anchor, part, frame["start"], end_offset,
                                        digest(data[frame["start"]:end_offset]),
                                        "".join(s.value for s in spans), spans, frame["nested"], heading_level, heading_style))

    parser.StartElementHandler = start
    parser.CharacterDataHandler = chars
    parser.EndElementHandler = end
    try:
        parser.Parse(data, True)
    except expat.ExpatError as exc:
        raise DocumentPackageError("INVALID_DOCUMENT_XML") from exc
    return sorted(blocks, key=lambda b: b.start)


def document_map(content: bytes) -> list[DocumentBlock]:
    parts = package_parts(content)
    style_headings: dict[str, tuple[int | None, str | None]] = {}
    style_bases: dict[str, str | None] = {}
    styles = parts.get("word/styles.xml", b"")
    for match in re.finditer(rb"<w:style\b([^>]*)>(.*?)</w:style>", styles, re.S):
        attrs, body = match.groups()
        style_id = re.search(rb"w:styleId=[\"']([^\"']+)", attrs)
        if not style_id or not re.search(rb"(?:w:)?type=[\"']paragraph[\"']", attrs):
            continue
        sid = style_id.group(1).decode("utf-8", "ignore")
        name_match = re.search(rb"<w:name\b[^>]*w:val=[\"']([^\"']+)", body)
        name = name_match.group(1).decode("utf-8", "ignore") if name_match else sid
        outline_match = re.search(rb"<w:outlineLvl\b[^>]*w:val=[\"'](\d+)", body)
        level = int(outline_match.group(1)) + 1 if outline_match else None
        heading_match = re.search(r"heading\s*([1-9])", f"{sid} {name}", re.I)
        if heading_match:
            level = level or int(heading_match.group(1))
        style_headings[sid] = (level, name)
        based_on = re.search(rb"<w:basedOn\b[^>]*w:val=[\"']([^\"']+)", body)
        style_bases[sid] = based_on.group(1).decode("utf-8", "ignore") if based_on else None
    for sid in list(style_headings):
        seen: set[str] = set()
        level, name = style_headings[sid]
        base = style_bases.get(sid)
        while level is None and base and base not in seen:
            seen.add(base)
            parent = style_headings.get(base)
            if parent:
                level, inherited_name = parent
                name = name or inherited_name
            base = style_bases.get(base)
        style_headings[sid] = (level, name)
    names = [n for n in parts if n == "word/document.xml" or re.fullmatch(r"word/(?:header|footer)\d+\.xml", n)]
    return [block for name in sorted(names) for block in _part_blocks(name, parts[name], style_headings)]


def _escape(value: str) -> bytes:
    if len(value) > 1000000:
        raise DocumentPackageError("TEXT_SIZE_LIMIT")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in value):
        raise DocumentPackageError("INVALID_TEXT_CHARACTER")
    # Line/paragraph breaks need explicit OOXML operations, never literal XML
    # text that Word can render differently from the browser editor.
    if any(c in value for c in "\t\n\r"):
        raise DocumentPackageError("STRUCTURAL_EDIT_REQUIRED")
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").encode("utf-8")


def apply_text_mutations(content: bytes, mutations: Iterable[TextMutation]) -> bytes:
    mutations = list(mutations)
    parts = package_parts(content)
    blocks = {b.anchor: b for b in document_map(content)}
    if len({m.anchor for m in mutations}) != len(mutations):
        raise DocumentPackageError("DUPLICATE_MUTATION_ANCHOR")
    edits: dict[str, list[tuple[int, int, bytes]]] = {}
    occupied: dict[str, list[tuple[int, int]]] = {}
    for mutation in mutations:
        block = blocks.get(mutation.anchor)
        if block is None:
            raise DocumentPackageError("DOCUMENT_ANCHOR_NOT_FOUND")
        if block.xml_hash != mutation.expected_xml_hash:
            raise DocumentPackageError("DOCUMENT_PRECONDITION_FAILED")
        if mutation.replacement == block.text:
            continue
        _escape(mutation.replacement)
        if block.has_nested_paragraphs or not block.text_spans:
            raise DocumentPackageError("COMPLEX_BLOCK_EDIT_REQUIRES_REVIEW")
        intervals = occupied.setdefault(block.part, [])
        if any(block.start < end and start < block.end for start, end in intervals):
            raise DocumentPackageError("OVERLAPPING_MUTATIONS")
        intervals.append((block.start, block.end))
        # Allocate characters to existing text runs, retaining all run formatting,
        # field/shape/table geometry, relationships and other XML bytes.
        remaining = mutation.replacement
        for i, span in enumerate(block.text_spans):
            value = remaining if i == len(block.text_spans) - 1 else remaining[:len(span.value)]
            remaining = remaining[len(value):]
            if value != span.value:
                # New boundary spaces without xml:space preservation need a
                # structural edit. Fail closed instead of silently losing them.
                tag_start = parts[block.part].rfind(b"<", block.start, span.start)
                tag = parts[block.part][tag_start:span.start]
                if value != value.strip(" ") and not re.search(rb'xml:space\s*=\s*[\"\']preserve[\"\']', tag):
                    raise DocumentPackageError("SPACE_PRESERVATION_REQUIRES_REVIEW")
                edits.setdefault(block.part, []).append((span.start, span.end, _escape(value)))
    if not edits:
        return content
    for part, changes in edits.items():
        data = parts[part]
        for start, end, replacement in sorted(changes, reverse=True):
            data = data[:start] + replacement + data[end:]
        parts[part] = data
    result = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(result, "w") as target:
        target.comment = source.comment
        for info in source.infolist():
            target.writestr(info, parts[info.filename])
    output = result.getvalue()
    package_parts(output)
    return output


def merge_text_mutations(previous_ai: bytes, current_owner: bytes, mutations: Iterable[TextMutation]) -> MergeResult:
    mutations = list(mutations)
    base = {b.anchor: b for b in document_map(previous_ai)}
    owner = {b.anchor: b for b in document_map(current_owner)}
    if base.keys() != owner.keys():
        # Ordinal fallback anchors are only valid for text-preserving topology.
        # A rich editor must supply persistent identities before structural edits
        # can be merged. Never guess at shifted paragraph/table coordinates.
        return MergeResult(current_owner, (), tuple({"anchor": m.anchor,
            "status": "NEEDS_OWNER_REVIEW", "reason": "DOCUMENT_STRUCTURE_CHANGED",
            "proposed": m.replacement} for m in mutations))
    safe = []
    conflicts = []
    for mutation in mutations:
        before, current = base.get(mutation.anchor), owner.get(mutation.anchor)
        if before is None or before.xml_hash != mutation.expected_xml_hash:
            raise DocumentPackageError("AI_BASE_PRECONDITION_FAILED")
        if current is None or current.xml_hash != before.xml_hash:
            conflicts.append({"anchor": mutation.anchor, "status": "NEEDS_OWNER_REVIEW", "current": current.text if current else "", "proposed": mutation.replacement})
        else:
            safe.append(mutation)
    return MergeResult(apply_text_mutations(current_owner, safe), tuple(m.anchor for m in safe), tuple(conflicts))
