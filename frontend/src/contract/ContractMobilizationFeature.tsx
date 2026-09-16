import { useCallback, useEffect, useRef, useState } from "react";
import { getContract } from "./contractApi";
import type { ContractData } from "./contractTypes";
import { ContractRegister } from "./ContractRegister";
import { ContractWorkspace } from "./ContractWorkspace";
import { navigateTo, useLocationPath } from "../navigation";
import { ApiError } from "../api";

export function ContractMobilizationFeature() {
  const location = useLocationPath();
  const contractId = location.match(/^\/contract-mobilization\/contracts\/([^/?#]+)/)?.[1] || null;
  const generation = useRef(0);
  const [data, setData] = useState<ContractData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const load = useCallback(async () => {
    const request = ++generation.current;
    if (!contractId) { setData(null); return; }
    setLoading(true);
    setError(null);
    try {
      const result = await getContract(contractId);
      if (request === generation.current) setData(result);
    } catch (cause) {
      const failure = cause instanceof Error ? cause : new Error("Contract could not be loaded.");
      if (request === generation.current) setError(failure);
      throw failure;
    } finally {
      if (request === generation.current) setLoading(false);
    }
  }, [contractId]);
  useEffect(() => {
    setData(null);
    void load().catch(() => undefined);
    return () => { generation.current++; };
  }, [load]);

  if (!contractId) return <div className="contract-feature-page"><ContractRegister onOpen={id => navigateTo(`/contract-mobilization/contracts/${id}`)} /></div>;
  return <div className="contract-feature-page" aria-busy={loading}>
    {error && <section className="contract-panel contract-error" role="alert">
      <h2>{data ? "Contract refresh failed" : "Contract workspace unavailable"}</h2>
      <p>{error.message}</p>
      {data && <p>The displayed record may be out of date. Refresh before performing another action.</p>}
      {error instanceof ApiError && error.correlationId && <details><summary>Support details</summary><p>Reference: {error.correlationId}</p></details>}
      <button className="button-secondary" onClick={() => void load().catch(() => undefined)} disabled={loading}>Retry</button>
      <button className="text-button" onClick={() => navigateTo("/contract-mobilization")}>Return to Contracts</button>
    </section>}
    {loading && <p role="status">{data ? "Refreshing Contract…" : "Loading Contract…"}</p>}
    {data && <fieldset className="contract-workspace-boundary" disabled={loading || Boolean(error)}>
      <ContractWorkspace key={data.id} data={data} onBack={() => navigateTo("/contract-mobilization")} onNavigate={navigateTo} onRefresh={load} />
    </fieldset>}
  </div>;
}
