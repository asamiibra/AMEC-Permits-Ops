import React, {
  Component,
  ErrorInfo,
  ReactNode,
} from "react";
import {
  createRoot,
} from "react-dom/client";

import App from "./App";
import { AuthFailureSurface } from "./AuthFailureSurface";
import {
  initializeBrowserAuthentication,
} from "./auth";
import {
  RebrandSurface,
} from "./rebrand";

import "./styles.css";
import "./proposal-realignment.css";
import "./persona-issues-notifications.css";
import "./admin-owner.css";
import "./amec-work.css";
import "./final-closure-accessibility.css";
import "./ui-productionization.css";
import "./ui-system-closure.css";
import "./mobile-navigation.css";


class AppErrorBoundary extends Component<
  {
    children: ReactNode;
  },
  {
    hasError: boolean;
  }
> {
  state = {
    hasError: false,
  };

  static getDerivedStateFromError() {
    return {
      hasError: true,
    };
  }

  componentDidCatch(
    error: Error,
    info: ErrorInfo,
  ) {
    console.error(
      "ProposalOps render boundary caught an error",
      error,
      info,
    );
  }

  render() {
    if (this.state.hasError) {
      return (
        <main
          className="app-error-boundary"
          role="alert"
        >
          <div className="panel">
            <span className="eyebrow">
              SAFE RECOVERY
            </span>
            <h1>
              ProposalOps could not render
              this screen
            </h1>
            <p>
              The current view stopped
              safely. Refresh the page or
              return to Home. No external
              action was performed.
            </p>
            <button
              className="button-primary"
              onClick={() => (
                window.location.assign(
                  "/home",
                )
              )}
            >
              Return to Home
            </button>
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}


function renderApplication() {
  const root =
    document.getElementById(
      "root",
    );

  if (!root) {
    throw new Error(
      "ProposalOps root element is missing",
    );
  }

  createRoot(
    root,
  ).render(
    <React.StrictMode>
      <AppErrorBoundary>
        <App />
        <RebrandSurface />
      </AppErrorBoundary>
    </React.StrictMode>,
  );
}


async function bootstrap() {
  const authState =
    await initializeBrowserAuthentication();

  if (
    authState
    === "REDIRECTING"
  ) {
    return;
  }

  renderApplication();
}


void bootstrap().catch(
  (error) => {
    console.error(
      "ProposalOps authentication startup failed",
      error,
    );

    const root =
      document.getElementById(
        "root",
      );

    if (root) {
      root.textContent = "";
      createRoot(root).render(<AuthFailureSurface />);
    }
  },
);
