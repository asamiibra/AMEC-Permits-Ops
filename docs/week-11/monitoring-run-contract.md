# Monitoring run contract

`MonitoringRun` is a durable correlation record for a due read. It carries scheduled time, application/policy, adapter and contract versions, prior/current snapshot IDs, status/result, attempt and retry class. A same application/policy/window claim is suppressed while a run is scheduled or running.
