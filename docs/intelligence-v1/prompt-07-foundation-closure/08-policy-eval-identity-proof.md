# Policy and eval identity proof

Shared policy rows are immutable by `(policy_code, version, immutable_hash)` and are included as snapshot governance dependencies. Eval packs have a small server-owned registry with immutable `(eval_pack_id, version, immutable_hash)` identity and critical-case/threshold policy fields.
