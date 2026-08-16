export function canonicalDomainRoute(raw: string | undefined, fallback: string): string {
  if (!raw) return fallback;
  try {
    const url = new URL(raw, window.location.origin);
    const path = url.pathname;
    if (path === "/admin/contracts/inputs/go-live") return `/admin/go-live-readiness${url.search}${url.hash}`;
    if (path === "/admin/contracts" || path === "/admin/contracts/") return `/contract-mobilization?view=contracts${url.search}${url.hash}`;
    if (path.startsWith("/admin/contracts/")) return `/contract-mobilization/contracts/${path.split("/")[3]}${url.search}${url.hash}`;
    if (path === "/admin/project-activation" || path === "/admin/project-activation/") return `/contract-mobilization?view=activation${url.search}${url.hash}`;
    if (path.startsWith("/admin/project-activation/")) return `/contract-mobilization/contracts/${path.split("/")[3]}?view=activation${url.hash}`;
    if (path === "/admin/invoices" || path === "/admin/invoices/") return `/billing${url.search}${url.hash}`;
    if (path.startsWith("/admin/invoices/")) return `/billing/invoices/${path.split("/")[3]}${url.search}${url.hash}`;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return fallback;
  }
}
