import React, { Component, ErrorInfo, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

class AppErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("PermitOps render boundary caught an error", error, info);
  }

  render() {
    if (this.state.hasError) {
      return <main className="app-error-boundary" role="alert"><div className="panel"><span className="eyebrow">SAFE RECOVERY</span><h1>PermitOps could not render this screen</h1><p>The current view stopped safely. Refresh the page or return to My Work. No external action was performed.</p><button className="button-primary" onClick={() => window.location.assign("/work")}>Return to My Work</button></div></main>;
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><AppErrorBoundary><App /></AppErrorBoundary></React.StrictMode>);
