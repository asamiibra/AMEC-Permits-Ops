# AuthorityEvent Contract

`AuthorityEvent` is the durable raw event boundary. It records project/application identity, source channel/type, external references, occurrence/capture time, raw evidence artifact, payload hash, normalized key, status, linked duplicate event, and a JSON payload safe for synthetic evidence.

Events are retained before normalization. The event is not a generic message bus. It supports synthetic precheck, portal-validation, manual official-comment, email-notice, and operator-capture paths.
