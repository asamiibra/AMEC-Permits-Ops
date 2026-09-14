export type PublicPage =
  | "home"
  | "opportunities"
  | "contract-mobilization"
  | "billing"
  | "content-library"
  | "work" | "engineering" | "regulatory" | "committee" | "construction" | "completion" | "handover" | "administration";

export type PublicRoute = {
  page: PublicPage;
  canonicalPath: string;
  allowed: boolean;
};

const startsWithRoute = (path: string, route: string) =>
  path === route || path.startsWith(`${route}/`);

/**
 * Positive allowlist for the current public release. A route is public only
 * when it belongs to Home or one of the active business modules; all other paths
 * resolve to Home without deleting their underlying domain implementation.
 */
export function classifyPublicRoute(pathname: string): PublicRoute {
  const path = pathname.replace(/\/+$/, "") || "/";

  if (path === "/" || path === "/home") {
    return { page: "home", canonicalPath: "/home", allowed: true };
  }
  if (path === "/work") {
    return { page: "work", canonicalPath: "/work", allowed: true };
  }
  const legacyContract = path.match(/^\/admin\/(?:contracts|project-activation)(?:\/([^/]+))?$/);
  if (legacyContract) {
    return { page: "contract-mobilization", canonicalPath: legacyContract[1] ? `/contract-mobilization/contracts/${legacyContract[1]}` : "/contract-mobilization", allowed: true };
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
  if (startsWithRoute(path, "/admin")) {
    return { page: "administration", canonicalPath: path, allowed: true };
  }
  const routes: Array<[string, PublicPage]> = [["/engineering", "engineering"], ["/regulatory", "regulatory"], ["/committee", "committee"], ["/construction", "construction"], ["/completion", "completion"], ["/handover", "handover"], ["/administration", "administration"]];
  for (const [prefix, page] of routes) if (startsWithRoute(path, prefix)) return { page, canonicalPath: path, allowed: true };
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

/**
 * Keep legacy deep-link consumers inside the current public shell. Historical
 * workspace components still import this helper, even though the Owner shell
 * now renders only the positive public allowlist above.
 */
export function canonicalDomainRoute(
  candidate: string | null | undefined,
  fallback = "/home",
): string {
  const requested = candidate?.trim() || fallback;
  return canonicalPublicPath(requested);
}
