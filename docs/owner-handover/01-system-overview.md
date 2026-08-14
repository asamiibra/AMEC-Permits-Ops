# System overview

The repository contains a frontend and FastAPI backend with PostgreSQL migrations through `0053_handover_admin_closeout`. Local development can use SQLite; the closure audit used durable local PostgreSQL. Synology, Excel, and municipality integrations observed in the audit are synthetic/mock adapters. Human decision and external verification gates are intentionally retained in the workflow.
