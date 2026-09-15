export type PublicPage =
  | "home"
  | "work"
  | "opportunities"
  | "contract-mobilization"
  | "project-delivery"
  | "billing"
  | "content-library"
  | "issues"
  | "notifications"
  | "owner-decisions"
  | "administration";

export type PublicRoute = { page: PublicPage; canonicalPath: string; allowed: boolean };
const startsWithRoute = (path: string, route: string) => path === route || path.startsWith(`${route}/`);

/** Work-oriented public routes. Historical Week/Phase/Source-numbered screens are not product navigation. */
export function classifyPublicRoute(pathname: string): PublicRoute {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/" || path === "/home") return { page: "home", canonicalPath: "/home", allowed: true };
  if (startsWithRoute(path, "/work")) return { page: "work", canonicalPath: path, allowed: true };
  if (startsWithRoute(path, "/opportunities") || path === "/bd" || startsWithRoute(path, "/bd/proposals") || startsWithRoute(path, "/proposals") || startsWithRoute(path, "/proposals-contracts")) return { page: "opportunities", canonicalPath: path, allowed: true };
  if (startsWithRoute(path, "/contract-mobilization") || startsWithRoute(path, "/contracts")) return { page: "contract-mobilization", canonicalPath: path, allowed: true };
  if (startsWithRoute(path, "/projects") || startsWithRoute(path, "/engineering") || startsWithRoute(path, "/engineering-closeout") || startsWithRoute(path, "/permits") || startsWithRoute(path, "/authority-cases") || startsWithRoute(path, "/construction") || startsWithRoute(path, "/completion") || startsWithRoute(path, "/handover") || startsWithRoute(path, "/source18/committee")) return { page: "project-delivery", canonicalPath: path, allowed: true };
  if (startsWithRoute(path, "/billing")) return { page: "billing", canonicalPath: path, allowed: true };
  if (startsWithRoute(path, "/content-library") || path === "/dashboard" || path === "/dashboard-v2" || startsWithRoute(path, "/library") || startsWithRoute(path, "/master-content")) return { page: "content-library", canonicalPath: path, allowed: true };
  if (startsWithRoute(path, "/issues")) return { page: "issues", canonicalPath: path, allowed: true };
  if (startsWithRoute(path, "/notifications")) return { page: "notifications", canonicalPath: path, allowed: true };
  if (startsWithRoute(path, "/owner-decisions") || startsWithRoute(path, "/admin/owner-decisions")) return { page: "owner-decisions", canonicalPath: path.replace(/^\/admin/, "") || "/owner-decisions", allowed: true };
  if (startsWithRoute(path, "/admin") && !startsWithRoute(path, "/admin/contracts") && !startsWithRoute(path, "/admin/project-activation")) return { page: "administration", canonicalPath: path, allowed: true };
  return { page: "home", canonicalPath: "/home", allowed: false };
}

export function isAllowedPublicRoute(pathname: string): boolean { return classifyPublicRoute(pathname).allowed; }
export function canonicalPublicPath(pathname: string): string { return classifyPublicRoute(pathname).canonicalPath; }
export function canonicalDomainRoute(candidate: string | null | undefined, fallback = "/home"): string { return canonicalPublicPath(candidate?.trim() || fallback); }
