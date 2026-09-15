import type { ReactNode } from "react";

export type RuntimeEnvironment =
  | "LOCAL_DEVELOPMENT"
  | "SYNTHETIC_TEST"
  | "OWNER_UAT"
  | "PREPRODUCTION"
  | "PRODUCTION"
  | "UNKNOWN";

const declaredEnvironments = new Set<RuntimeEnvironment>([
  "SYNTHETIC_TEST",
  "OWNER_UAT",
  "PREPRODUCTION",
  "PRODUCTION",
]);

export function runtimeEnvironment(): RuntimeEnvironment {
  if (import.meta.env.DEV) return "LOCAL_DEVELOPMENT";
  const value = String(import.meta.env.VITE_APP_ENV || "").trim().toUpperCase() as RuntimeEnvironment;
  return declaredEnvironments.has(value) ? value : "UNKNOWN";
}

export function environmentIndicator(environment: RuntimeEnvironment): string {
  switch (environment) {
    case "LOCAL_DEVELOPMENT": return "LOCAL DEVELOPMENT";
    case "SYNTHETIC_TEST": return "SYNTHETIC TEST";
    case "OWNER_UAT": return "OWNER UAT · SYNTHETIC";
    case "PREPRODUCTION": return "PREPRODUCTION";
    case "PRODUCTION": return "PRODUCTION";
    default: return "ENVIRONMENT UNDECLARED";
  }
}

export function isSyntheticEnvironment(environment: RuntimeEnvironment): boolean {
  return ["LOCAL_DEVELOPMENT", "SYNTHETIC_TEST", "OWNER_UAT", "PREPRODUCTION"].includes(environment);
}

export function EnvironmentBlockedSurface(): ReactNode {
  return (
    <main className="environment-blocked-surface" role="alert">
      <h1>Workspace unavailable</h1>
      <p>The runtime environment is not declared. Access is closed until deployment configuration identifies the environment.</p>
      <small>UNKNOWN_ENVIRONMENT_FAIL_CLOSED</small>
    </main>
  );
}
