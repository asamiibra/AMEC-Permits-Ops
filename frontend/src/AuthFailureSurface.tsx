export function AuthFailureSurface() {
  return (
    <main className="auth-failure-shell" aria-labelledby="auth-failure-title">
      <section className="auth-failure-card" role="alert" aria-live="assertive">
        <span className="eyebrow">SECURE ACCESS</span>
        <h1 id="auth-failure-title">ProposalOps couldn’t start sign-in</h1>
        <p>
          Try again to continue. If the problem continues, contact your system
          administrator.
        </p>
        <button
          className="button-primary"
          type="button"
          onClick={() => window.location.reload()}
        >
          Retry sign-in
        </button>
      </section>
    </main>
  );
}
