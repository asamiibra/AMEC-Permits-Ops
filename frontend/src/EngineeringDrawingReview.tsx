import { useEffect, useState } from "react";
import { api } from "./api";

type Project = { id: string; project_number: string; project_name: string };
type Category = { id: string; code: string; name: string };
type ReviewItem = { id: string; review_category?: Category | null; discipline?: string; revision?: { revision_code?: string }; date?: string; status: string; lane: string; action: string; renditions: Array<{ id: string; rendition_kind: string }> };
type ReviewDetail = ReviewItem & { deliverable?: { deliverable_ref?: string; title?: string }; findings: any[]; internal_comments: any[]; ai_comment_artifacts: any[]; authority_links: any[]; revision_policy: { business_format: string; document_version_is_separate: boolean } };

export function EngineeringDrawingReviewPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selected, setSelected] = useState<ReviewDetail | null>(null);
  const [lane, setLane] = useState("ALL");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = async (id: string, nextLane = lane) => {
    if (!id) return;
    try {
      const [reviewList, categoryList] = await Promise.all([
        api<{ items: ReviewItem[] }>(`/api/projects/${id}/engineering/drawing-review?lane=${nextLane}`),
        api<{ categories: Category[] }>(`/api/projects/${id}/engineering/review-categories`),
      ]);
      setItems(reviewList.items); setCategories(categoryList.categories); setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Drawing Review is unavailable."); }
  };
  useEffect(() => { api<Project[]>("/api/projects").then(async list => { setProjects(list); const first = list[0]?.id || ""; setProjectId(first); await load(first); }).catch(() => setError("Canonical Project register is unavailable.")); }, []);
  useEffect(() => { if (projectId) load(projectId, lane); }, [lane]);
  const open = async (id: string) => { try { setSelected(await api<ReviewDetail>(`/api/projects/${projectId}/engineering/drawing-review/${id}`)); setError(""); } catch (cause) { setError(cause instanceof Error ? cause.message : "Review detail is unavailable."); } };
  const setCategory = async (categoryId: string) => { if (!selected || !categoryId) return; try { setSelected(await api<ReviewDetail>(`/api/projects/${projectId}/engineering/reviews/${selected.id}/review-category`, { method: "POST", body: JSON.stringify({ review_category_id: categoryId }) })); setMessage("Review Category assigned. Discipline remains a separate field."); await load(projectId); } catch (cause) { setError(cause instanceof Error ? cause.message : "Category assignment was blocked."); } };
  const generateAi = async () => { if (!selected) return; try { await api(`/api/projects/${projectId}/engineering/drawing-review/${selected.id}/ai-comments`, { method: "POST", body: JSON.stringify({}) }); setMessage("AI-assisted / draft comment generated; no approval or authority finding changed."); await open(selected.id); } catch (cause) { setError(cause instanceof Error ? cause.message : "AI draft generation was blocked."); } };

  return <div className="workflow-page expansion-workspace">
    <div className="page-intro"><div><span className="eyebrow">ENGINEERING · DRAWING REVIEW</span><h2>Drawing Review</h2><p>Review Category, exact business revision, pinned Drawing/PDF evidence, internal comments, and draft-only AI assistance.</p></div><span className="tag">Human-controlled</span></div>
    <div className="synthetic-note">INTERNAL ENGINEERING REVIEW / CANONICAL EXTERNAL LINK ONLY · NOT AUTHORITY APPROVAL · NOT CONSTRUCTION RELEASE</div>
    <section className="panel expansion-context"><div><b>Project context</b><small>Every review, rendition, comment, assignment, and AI artifact is project-scoped.</small></div><select aria-label="Project context" value={projectId} onChange={event => { setProjectId(event.target.value); setSelected(null); load(event.target.value); }}>{projects.map(project => <option key={project.id} value={project.id}>{project.project_number} · {project.project_name}</option>)}</select></section>
    {message && <div className="inline-message" role="status">{message}</div>}{error && <div className="error-banner">{error}</div>}
    <section className="panel"><div className="panel-head"><div><span className="eyebrow">OWNER WORKSPACE</span><h3>Review queue</h3></div><select aria-label="Review lane" value={lane} onChange={event => setLane(event.target.value)}>{["ALL", "NEED_ACTION", "AUTHORITY_REVIEW", "READY_CLOSE"].map(value => <option key={value}>{value}</option>)}</select></div><div className="review-table"><div className="review-table-head"><span>Project</span><span>Review Category</span><span>Revision</span><span>Date</span><span>Status / Action</span></div>{items.length ? items.map(item => <button className="review-row" key={item.id} onClick={() => open(item.id)}><span>{projects.find(project => project.id === projectId)?.project_number || projectId.slice(0, 8)}</span><span>{item.review_category?.name || "Unassigned"}<small>{item.review_category?.code || "CATEGORY_REQUIRED"} · discipline is separate</small></span><span>{item.revision?.revision_code || "—"}</span><span>{item.date ? new Date(item.date).toLocaleDateString() : "—"}</span><span><b>{item.status}</b><small>{item.action}</small></span></button>) : <p className="muted">No Drawing Review records for this project yet.</p>}</div></section>
    {selected && <section className="panel"><div className="panel-head"><div><span className="eyebrow">EXACT REVIEW DETAIL</span><h3>{selected.deliverable?.deliverable_ref || "Drawing review"} · {selected.revision?.revision_code}</h3><small>{selected.deliverable?.title} · {selected.discipline || "Discipline not set"}</small></div><span className="tag">{selected.lane}</span></div><div className="form-grid"><label>Review Category<select aria-label="Review Category" value={selected.review_category?.id || ""} onChange={event => setCategory(event.target.value)}><option value="">Select configured category</option>{categories.map(category => <option key={category.id} value={category.id}>{category.code} · {category.name}</option>)}</select></label><div><span className="eyebrow">REVISION POLICY</span><p className="muted">{selected.revision_policy.business_format}; DocumentVersion remains separate; exact revision is pinned.</p></div></div><div className="detail-actions">{selected.renditions.map(rendition => <a className="button-secondary" key={rendition.id} href={`/api/projects/${projectId}/engineering/drawing-review/${selected.id}/renditions/${rendition.id}/download`} target="_blank" rel="noreferrer">Open {rendition.rendition_kind} / PDF</a>)}<button className="button-primary" onClick={generateAi}>Generate AI draft</button></div><div className="boundary-grid"><div><b>{selected.findings.length}</b><small>Review findings</small></div><div><b>{selected.internal_comments.length}</b><small>Internal comments</small></div><div><b>{selected.ai_comment_artifacts.length}</b><small>AI-assisted drafts</small></div><div><b>{selected.authority_links.length}</b><small>Canonical external links</small></div></div></section>}
  </div>;
}
