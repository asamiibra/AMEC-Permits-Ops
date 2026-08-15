# Existing Proposal render root cause

The risk was a combination of fragile assumptions about nullable API collections/strings and route/load state that could retain a stale detail shell after a failed load. Examples included direct string operations on optional treatment/status values and unguarded nested configuration data.

The backend detail payload was not replaced with a synthetic empty object. Instead, the frontend now validates the core detail contract, normalizes optional areas, guards nullable display values, and makes loading/error/not-found states explicit. This preserves the existing Proposal and Forms-v2 data while preventing optional data from becoming a render exception.
