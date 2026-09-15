import { AuthorityCaseWorkspacePage } from "./AuthorityCaseWorkspace";
import { CompletionPage } from "./Completion";
import { ConstructionPage } from "./Construction";
import { EngineeringCloseoutPage } from "./EngineeringCloseout";
import { EngineeringDrawingReviewPage } from "./EngineeringDrawingReview";
import { HandoverPage } from "./Handover";
import { PermitCasePage, PermitPortfolioPage, NewPermitPage } from "./PermitAuthorityUX";
import { ProjectEngineeringPage } from "./ProjectEngineering";
import { Source18CommitteePage } from "./Source18Committee";

/**
 * One Projects & Delivery workspace with contextual routes for the actual
 * delivery lifecycle. These are real domain screens, not historical phase
 * pages; protected actions remain governed by the API.
 */
export function ProductDeliveryPage() {
  const path = window.location.pathname;
  if (path === "/engineering/drawing-review") return <EngineeringDrawingReviewPage />;
  if (path === "/engineering-closeout") return <EngineeringCloseoutPage />;
  if (path === "/permits/new") return <NewPermitPage />;
  if (path.startsWith("/permits/") && path !== "/permits/new") return <PermitCasePage />;
  if (path === "/permits") return <PermitPortfolioPage />;
  if (path.startsWith("/authority-cases/")) return <AuthorityCaseWorkspacePage />;
  if (path === "/construction" || path.startsWith("/construction/")) return <ConstructionPage />;
  if (path === "/completion" || path.startsWith("/completion/")) return <CompletionPage />;
  if (path === "/handover" || path.startsWith("/handover/")) return <HandoverPage />;
  if (path === "/source18/committee") return <Source18CommitteePage />;
  return <ProjectEngineeringPage />;
}
