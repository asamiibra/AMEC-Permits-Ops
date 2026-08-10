# RBAC and security

Backend capability enforcement is authoritative: Owner/System Admin can write all master content and Definitions; Business Development and Engineering are read-only for global master content. Direct API negative tests prove Business Development write denial. The backend owns SOR credentials by design; this repository contains none. Filename normalization, extension allowlisting, file-size limits, path containment, hashing, and authenticated backend download are implemented.
