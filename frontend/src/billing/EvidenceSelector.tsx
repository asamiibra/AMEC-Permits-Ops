import { useEffect, useState } from "react";
import { billingApi } from "./billing-api";
import type { BillingEvidenceItem } from "./billing-types";

export function EvidenceSelector({ projectId, value, onChange, label = "Canonical evidence", allowEmpty = true }: { projectId?: string | null; value: string; onChange: (value: string) => void; label?: string; allowEmpty?: boolean }) {
  const [items, setItems] = useState<BillingEvidenceItem[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { let live = true; void billingApi.evidence(projectId).then((result) => { if (live) setItems(result.items); }).catch((cause: unknown) => { if (live) setError(cause instanceof Error ? cause.message : "Evidence library unavailable."); }); return () => { live = false; }; }, [projectId]);
  const selected = items.find((item) => item.document_version_id === value);
  return <div className="billing-evidence-selector"><label>{label}<select value={value} onChange={(event) => onChange(event.target.value)}><option value="">{allowEmpty ? "No evidence selected" : "Select evidence"}</option>{items.map((item) => <option value={item.document_version_id} key={item.document_version_id}>{item.label} · {item.filename} · {item.approval_state}</option>)}</select></label>{selected && <small><a href={selected.open_path} target="_blank" rel="noreferrer">Open evidence</a> · {selected.approval_state}</small>}{error && <small className="billing-error">{error}</small>}</div>;
}
