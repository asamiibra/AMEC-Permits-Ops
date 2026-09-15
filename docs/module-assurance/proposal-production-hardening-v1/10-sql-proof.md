# SQL proof

Repository SQL Server portability/static sanity suite passes (31 checks in `test_azure_sql_port.py`); the native SQL Server runtime gate requires an explicitly provisioned `mssql+pyodbc` application DSN and was not executed. The visible Docker SQL Server container is not treated as an application qualification without an authorized DSN/configuration.
