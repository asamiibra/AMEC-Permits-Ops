# Package Staleness Contract

An approved package retains its original manifest hash, source truth hash, item versions, and approval audit. A material upstream change marks it `STALE`; approval of the stale package is rejected. Rebuild creates a distinct draft package and never mutates the old package.
