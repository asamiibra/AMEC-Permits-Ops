from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models import (
    AuthorityCase, AuthorityCaseFinding, Document, DocumentVersion, EngineeringAICommentArtifact,
    EngineeringAuthorityFindingLink, EngineeringCategoryAssignment, EngineeringDeliverable,
    EngineeringDeliverableRevision, EngineeringInternalReviewComment, EngineeringProjectMember,
    EngineeringRendition, EngineeringReviewCategory, EngineeringReviewFinding, EngineeringWorkPackage,
    LineageEdge, Project, ProjectEngineeringReview,
)


def _headers(role="RESPONSIBLE_ENGINEER", actor="drawing-review-engineer"):
    return {"X-Dev-Role": role, "X-Dev-Actor": actor}


def _project(client: TestClient, number: str) -> str:
    response = client.post("/api/projects", json={"project_number": number, "project_name": "Drawing Review Synthetic", "municipality": "Synthetic Municipality", "permit_type": "Building"})
    assert response.status_code == 200, response.text
    project_id = response.json()["id"]
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        project.activated_at = datetime.now(timezone.utc)
        project.activated_by = "synthetic-owner"
        db.commit()
    return project_id


def _cleanup(project_id: str) -> None:
    with SessionLocal() as db:
        revision_ids = select(EngineeringDeliverableRevision.id).where(EngineeringDeliverableRevision.project_id == project_id)
        review_ids = select(ProjectEngineeringReview.id).where(ProjectEngineeringReview.project_id == project_id)
        document_ids = select(Document.id).where(Document.project_id == project_id)
        for model, field in (
            (EngineeringAuthorityFindingLink, EngineeringAuthorityFindingLink.project_id),
            (EngineeringAICommentArtifact, EngineeringAICommentArtifact.project_id),
            (EngineeringInternalReviewComment, EngineeringInternalReviewComment.project_id),
            (EngineeringReviewFinding, EngineeringReviewFinding.project_id),
            (EngineeringRendition, EngineeringRendition.project_id),
            (ProjectEngineeringReview, ProjectEngineeringReview.project_id),
            (EngineeringDeliverableRevision, EngineeringDeliverableRevision.project_id),
            (EngineeringCategoryAssignment, EngineeringCategoryAssignment.project_id),
            (EngineeringProjectMember, EngineeringProjectMember.project_id),
            (EngineeringWorkPackage, EngineeringWorkPackage.project_id),
            (LineageEdge, LineageEdge.project_id),
        ):
            db.execute(delete(model).where(field == project_id))
        db.execute(update(EngineeringDeliverable).where(EngineeringDeliverable.project_id == project_id).values(current_revision_id=None))
        db.execute(delete(DocumentVersion).where(DocumentVersion.document_id.in_(document_ids)))
        db.execute(delete(Document).where(Document.project_id == project_id))
        db.execute(delete(EngineeringDeliverable).where(EngineeringDeliverable.project_id == project_id))
        db.execute(delete(Project).where(Project.id == project_id))
        db.commit()


def test_drawing_review_category_assignment_exact_pdf_and_ai_draft_are_separate():
    with TestClient(app) as client:
        project_id = _project(client, "ENG-DRAWING-RECON")
        try:
            owner = _headers("OWNER_SPONSOR", "owner-reviewer")
            engineer = _headers()
            bd = _headers("COMMERCIAL_APPROVER", "commercial-reviewer")
            category_response = client.post("/api/engineering/review-categories", headers=owner, json={"code": "OWNER_DRAWING_CHECK", "name": "Owner Drawing Check", "discipline": "ARCHITECTURE", "stage_class": "INTERNAL_REVIEW"})
            assert category_response.status_code == 200, category_response.text
            category = category_response.json()
            package = client.post(f"/api/projects/{project_id}/engineering/work-packages", headers=engineer, json={"package_ref": "WP-DRAWING", "title": "Drawing package", "discipline": "ARCHITECTURE"}).json()
            deliverable = client.post(f"/api/projects/{project_id}/engineering/deliverables", headers=engineer, json={"work_package_id": package["id"], "deliverable_ref": "DR-001", "title": "Owner drawing", "discipline": "ARCHITECTURE"}).json()
            revision_one = client.post(f"/api/projects/{project_id}/engineering/deliverables/{deliverable['id']}/revisions", headers=engineer, json={}).json()
            revision_two = client.post(f"/api/projects/{project_id}/engineering/deliverables/{deliverable['id']}/revisions", headers=engineer, json={}).json()
            assert (revision_one["revision_code"], revision_two["revision_code"]) == ("R1", "R2")
            published = client.post(f"/api/projects/{project_id}/engineering/revisions/{revision_one['id']}/ingest", headers=engineer, json={"rendition_kind": "PUBLISHED", "filename": "owner-drawing-r1.pdf", "mime_type": "application/pdf", "synthetic_content": "EXACT-R1-PDF"}).json()
            client.post(f"/api/projects/{project_id}/engineering/revisions/{revision_one['id']}/ingest", headers=engineer, json={"rendition_kind": "NATIVE", "filename": "owner-drawing-r1.native", "synthetic_content": "EXACT-R1-NATIVE"})
            review = client.post(f"/api/projects/{project_id}/engineering/revisions/{revision_one['id']}/reviews", headers=engineer, json={"review_category_id": category["id"]}).json()
            assert review["review_category_id"] == category["id"]
            assignment = client.post(f"/api/projects/{project_id}/engineering/review-categories/{category['id']}/assignments", headers=engineer, json={"assignee_actor": "drawing-owner", "responsibility": "CATEGORY_REVIEW"})
            assert assignment.status_code == 200, assignment.text
            assert client.post(f"/api/projects/{project_id}/engineering/review-categories/{category['id']}/assignments", headers=bd, json={"assignee_actor": "not-allowed"}).status_code == 403
            comment = client.post(f"/api/projects/{project_id}/engineering/drawing-review/{review['id']}/internal-comments", headers=engineer, json={"document_version_id": published["document_version"]["id"], "comment_text": "Internal coordination note"})
            assert comment.status_code == 200, comment.text
            listing = client.get(f"/api/projects/{project_id}/engineering/drawing-review", headers=owner).json()
            assert listing["columns"][:3] == ["project", "review_category", "revision"]
            assert listing["items"][0]["revision"]["id"] == revision_one["id"]
            download = client.get(f"/api/projects/{project_id}/engineering/drawing-review/{review['id']}/renditions/{published['rendition']['id']}/download", headers=owner)
            assert download.status_code == 200 and download.content == b"EXACT-R1-PDF"
            opened = client.get(f"/api/projects/{project_id}/engineering/drawing-review/{review['id']}/renditions/{published['rendition']['id']}/open", headers=owner)
            assert opened.status_code == 200 and opened.json()["exact_reference"] is True and opened.json()["document_version"]["id"] == published["document_version"]["id"]
            artifact = client.post(f"/api/projects/{project_id}/engineering/drawing-review/{review['id']}/ai-comments", headers=engineer, json={})
            assert artifact.status_code == 200 and artifact.json()["status"] == "AI_ASSISTED_DRAFT"
            detail = client.get(f"/api/projects/{project_id}/engineering/drawing-review/{review['id']}", headers=owner).json()
            assert detail["internal_comments"][0]["comment_text"] == "Internal coordination note"
            assert detail["ai_comment_artifacts"][0]["status"] == "AI_ASSISTED_DRAFT"
            assert detail["professional_approval"] == []
            seam = client.get(f"/api/projects/{project_id}/engineering/drawing-review/{review['id']}/authority-comment-seam", headers=owner).json()
            assert seam["canonical_type"] == "AuthorityCaseFinding" and seam["creates_external_truth"] is False
        finally:
            _cleanup(project_id)
