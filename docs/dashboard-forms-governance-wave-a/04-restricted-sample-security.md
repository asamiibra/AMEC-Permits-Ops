# Restricted sample security

Restricted/project-specific samples are represented as governed metadata and are excluded from canonical downstream resolution. Ordinary list/search responses expose metadata only; restricted preview/download requires the restricted capability and the backend checks it again on the download path.

The Wave A contract suite verifies restricted samples cannot resolve as canonical forms and that unauthorized download is rejected.
