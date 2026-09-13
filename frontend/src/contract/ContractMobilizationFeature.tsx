import { useEffect, useState } from "react";
import { api } from "../api";
import type { ContractData } from "./contractTypes";
import { ContractRegister } from "./ContractRegister";
import { ContractWorkspace } from "./ContractWorkspace";

export function ContractMobilizationFeature() {
  const [path, setPath] = useState(window.location.pathname);
  const [data, setData] = useState<ContractData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const contractId = path.match(/^\/contract-mobilization\/contracts\/([^/]+)/)?.[1] || null;
  const navigate = (route: string) => { window.history.pushState({}, "", route); window.dispatchEvent(new PopStateEvent("popstate")); };
  useEffect(() => { const sync = () => setPath(window.location.pathname); window.addEventListener("popstate", sync); return () => window.removeEventListener("popstate", sync); }, []);
  useEffect(() => { const legacyContract = window.location.pathname.match(/^\/admin\/contracts(?:\/([^/]+))?/); const legacyActivation = window.location.pathname.match(/^\/admin\/project-activation(?:\/([^/]+))?/); if (legacyContract || legacyActivation) { const id = legacyContract?.[1] || legacyActivation?.[1]; navigate(id ? `/contract-mobilization/contracts/${id}` : "/contract-mobilization"); } }, []);
  useEffect(() => { if (!contractId) { setData(null); return; } setLoading(true); setError(""); api<ContractData>(`/api/admin/contracts/${contractId}`).then(setData).catch((cause) => setError(cause instanceof Error ? cause.message : "Contract could not be loaded.")).finally(() => setLoading(false)); }, [contractId]);
  if (!contractId) return <div className="contract-feature-page"><ContractRegister onOpen={(id) => navigate(`/contract-mobilization/contracts/${id}`)} /></div>;
  if (loading || !data) return <div className="contract-feature-page"><section className="contract-panel contract-loading" role="status">{error ? <><h1>Contract workspace unavailable</h1><p>{error}</p><button className="button-secondary" onClick={() => navigate("/contract-mobilization")}>Return to Contracts</button></> : <strong>Loading canonical Contract workspace…</strong>}</section></div>;
  return <div className="contract-feature-page"><ContractWorkspace data={data} onBack={() => navigate("/contract-mobilization")} onNavigate={navigate} onRefresh={() => { api<ContractData>(`/api/admin/contracts/${contractId}`).then(setData).catch(() => {}); }} /></div>;
}
