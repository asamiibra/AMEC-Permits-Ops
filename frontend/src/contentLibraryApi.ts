import { api } from "./api";

export type CanonicalFormReadFilters = {
  q?: string;
  category_label?: string;
  owner_status?: string;
  module?: string;
  ownership?: string;
  artifact_kind?: string;
  publisher?: string;
  currentness?: string;
  wave_a_readiness?: string;
  automation_readiness?: string;
  quality_state?: string;
  restricted_sample?: string;
  language?: string;
  external_body_id?: string;
  jurisdiction_id?: string;
  service_type_id?: string;
  lifecycle_phase_id?: string;
  applicability_status?: string;
};

const canonicalQuery = (filters: CanonicalFormReadFilters = {}) => {
  const params = new URLSearchParams({ content_type: "FORM" });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  return params;
};

/** All business Form reads use the canonical MasterContent read contract. */
export function readCanonicalForms<T>(filters: CanonicalFormReadFilters = {}) {
  return api<T[]>(`/api/master-content?${canonicalQuery(filters)}`);
}

export function readCanonicalForm<T>(itemId: string) {
  return api<T>(`/api/master-content/${itemId}`);
}

export function readCanonicalFormCatalogs<T>() {
  return api<T>("/api/master-content/catalogs");
}
