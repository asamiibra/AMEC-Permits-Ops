export type PublicPage =
  | "home"
  | "opportunities"
  | "contract-mobilization"
  | "billing"
  | "content-library";

export type PublicRoute = {
  page: PublicPage;
  canonicalPath: string;
  allowed: boolean;
};

const startsWithRoute = (path: string, route: string) =>
  path === route || path.startsWith(`${route}/`);

/**
 * Positive allowlist for the current public release. A route is public only
 * when it belongs to Home or one of the four active modules; all other paths
 * resolve to Home without deleting their underlying domain implementation.
 */
export function classifyPublicRoute(pathname: string): PublicRoute {
  const path = pathname.replace(/\/+$/, "") || "/";

  if (path === "/" || path === "/home") {
    return { page: "home", canonicalPath: "/home", allowed: true };
  }
  if (path === "/work") {
    return { page: "home", canonicalPath: "/home", allowed: false };
  }
  if (startsWithRoute(path, "/opportunities") || path === "/bd" || startsWithRoute(path, "/bd/proposals")) {
    return { page: "opportunities", canonicalPath: path, allowed: true };
  }
  if (startsWithRoute(path, "/contract-mobilization")) {
    return { page: "contract-mobilization", canonicalPath: path, allowed: true };
  }
  if (startsWithRoute(path, "/billing")) {
    return { page: "billing", canonicalPath: path, allowed: true };
  }
  if (
    startsWithRoute(path, "/content-library") ||
    path === "/dashboard" ||
    path === "/dashboard-v2" ||
    startsWithRoute(path, "/library") ||
    startsWithRoute(path, "/master-content")
  ) {
    return { page: "content-library", canonicalPath: path, allowed: true };
  }
  return { page: "home", canonicalPath: "/home", allowed: false };
}

export function isAllowedPublicRoute(pathname: string): boolean {
  return classifyPublicRoute(pathname).allowed;
}

export function canonicalPublicPath(pathname: string): string {
  return classifyPublicRoute(pathname).canonicalPath;
}
