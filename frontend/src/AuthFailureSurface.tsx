export type AuthzSurfaceState =
  | "AUTHZ_LOADING"
  | "AUTHZ_UNMAPPED"
  | "AUTHZ_UNSUPPORTED_ROLE"
  | "AUTHZ_UNAUTHENTICATED"
  | "AUTHZ_ERROR";

const copy: Record<AuthzSurfaceState, { title: string; body: string; action: string }> = {
  AUTHZ_LOADING: {
    title: "Securing AMEC System",
    body: "Verifying your AMEC System access…",
    action: "Please wait",
  },
  AUTHZ_UNMAPPED: {
    title: "Access not configured",
    body: "Your Microsoft Entra identity is authenticated, but it is not mapped to an active AMEC System user.",
    action: "Sign out",
  },
  AUTHZ_UNSUPPORTED_ROLE: {
    title: "Role not enabled for this release",
    body: "Your AMEC System role is valid but is not enabled for this four-module release.",
    action: "Sign out",
  },
  AUTHZ_UNAUTHENTICATED: {
    title: "AMEC System couldn’t verify your session",
    body: "Your sign-in session is no longer valid. Retry sign-in to continue.",
    action: "Retry sign-in",
  },
  AUTHZ_ERROR: {
    title: "AMEC System is temporarily unavailable",
    body: "Access could not be verified right now. Retry, or sign out and try again later.",
    action: "Retry",
  },
};

export function AuthzSurface({ state, identity, role, onRetry, onSignOut, busy = false }: {
  state: AuthzSurfaceState;
  identity?: string;
  role?: string;
  onRetry?: () => void;
  onSignOut?: () => void;
  busy?: boolean;
}) {
  const content = copy[state];
  const action = state === "AUTHZ_UNMAPPED" || state === "AUTHZ_UNSUPPORTED_ROLE" ? onSignOut : onRetry;
  return (
    <main className="auth-failure-shell" aria-labelledby="auth-failure-title">
      <section className="auth-failure-card" role={state === "AUTHZ_LOADING" ? undefined : "alert"} aria-live="assertive">
        <span className="eyebrow">SECURE ACCESS</span>
        <h1 id="auth-failure-title">{content.title}</h1>
        <p>{content.body}</p>
        {identity && <p><strong>{identity}</strong>{role && ` · ${role}`}</p>}
        {state !== "AUTHZ_LOADING" && action && (
          <button className="button-primary" type="button" onClick={action} disabled={busy}>
            {busy ? "Signing out…" : content.action}
          </button>
        )}
      </section>
    </main>
  );
}

export function AuthFailureSurface() {
  return (
    <AuthzSurface state="AUTHZ_UNAUTHENTICATED" onRetry={() => window.location.reload()} />
  );
}
