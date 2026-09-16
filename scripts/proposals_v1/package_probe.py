"""Reproduce a narrow preservation probe; output is QA, not a Proposal draft.

Run from repository root with an explicitly supplied local acceptance DOCX.
No baseline/client bytes or extracted text are committed by this script.
"""
import argparse
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.services.proposal_document_package import (
    TextMutation, apply_text_mutations, digest, document_map, package_parts,
)

parser = argparse.ArgumentParser()
parser.add_argument('baseline', type=Path)
parser.add_argument('output_dir', type=Path)
args = parser.parse_args()
source = args.baseline.read_bytes()
blocks = document_map(source)
matches = [b for b in blocks if b.text == 'Duration: 3 months']
if len(matches) != 1:
    raise SystemExit('Controlled duration anchor is not unique; refusing to guess')
block = matches[0]
result = apply_text_mutations(source, [TextMutation(block.anchor, block.xml_hash, 'Duration: 4 months')])
before, after = package_parts(source), package_parts(result)
changed = [name for name in before if before[name] != after[name]]
if changed != ['word/document.xml']:
    raise SystemExit('Unexpected changed package parts')
if before['word/document.xml'].replace(b'>3 months<', b'>4 months<') != after['word/document.xml']:
    raise SystemExit('Unexpected XML mutation outside duration text')
args.output_dir.mkdir(parents=True, exist_ok=True)
output = args.output_dir / 'controlled-duration.docx'
if output.resolve() == args.baseline.resolve() or output.exists():
    raise SystemExit('Output must be a new file separate from the baseline')
output.write_bytes(result)
report = {
    'purpose': 'QA controlled mutation, not factual Project 454 output',
    'baseline_sha256': digest(source), 'output_sha256': digest(result),
    'changed_parts': changed, 'unchanged_part_count': len(before) - len(changed),
    'anchor_count': len(blocks), 'target_anchor': block.anchor,
    'parts': [{ 'path': name, 'size': len(data), 'sha256': digest(data)} for name, data in before.items()],
}
(args.output_dir / 'package-probe.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='parts'},indent=2))
