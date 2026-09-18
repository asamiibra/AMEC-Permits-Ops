# Package preservation

Implemented targeted text-node mutation without XML reserialization or DOCX reconstruction. The document map covers body, tables, nested text-box paragraphs, headers and footers. It uses expanded XML-name structural paths plus hashes; whole-paragraph byte hashes protect preconditions.

No-op returns the original bytes. Changed exports preserve package member bytes except the affected XML text spans. ZIP member metadata is reused. Relationships and XML are validated before returning a new byte buffer. Original bytes are never overwritten.

Limitations: this primitive is text-only, not a Word editor. New paragraphs, formatting commands, images, fields, structural moves and full semantic classification require more work. Complex parent paragraphs, structural edits and ambiguous boundary-space edits fail closed. Positional anchors do not support arbitrary rich-editor restructuring.
