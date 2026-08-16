import React, { Component, ErrorInfo, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { RebrandSurface } from "./rebrand";
import "./styles.css";
import "./proposal-realignment.css";
import "./persona-issues-notifications.css";
import "./admin-owner.css";
import "./amec-work.css";
import "./final-closure-accessibility.css";
import "./ui-productionization.css";
import "./ui-system-closure.css";

class AppErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ProposalOps render boundary caught an error", error, info);
  }

  render() {
    if (this.state.hasError) {
      return <main className="app-error-boundary" role="alert"><div className="panel"><span className="eyebrow">SAFE RECOVERY</span><h1>ProposalOps could not render this screen</h1><p>The current view stopped safely. Refresh the page or return to Home. No external action was performed.</p><button className="button-primary" onClick={() => window.location.assign("/home")}>Return to Home</button></div></main>;
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><AppErrorBoundary><App /><RebrandSurface /></AppErrorBoundary></React.StrictMode>);
