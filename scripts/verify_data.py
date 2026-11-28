"""Quick verification of row counts and HSHD_NUM=10 before building the app."""

import os
import mssql_python

server = os.environ["SQL_SERVER"]
if not server.endswith(".database.windows.net"):
    server += ".database.windows.net"

conn = mssql_python.connect(
    server=server,
    database=os.environ["SQL_DB"],
    uid=os.environ["SQL_ADMIN"],
    pwd=os.environ["SQL_PASSWORD"],
    encrypt="yes",
    trustservercertificate="no",
)
cur = conn.cursor()
for t in ("households", "products", "transactions"):
    cur.execute(f"SELECT COUNT(*) FROM dbo.[{t}]")
    print(f"{t}: {cur.fetchone()[0]:,}")

cur.execute("SELECT COUNT(*) FROM dbo.transactions WHERE HSHD_NUM = 10")
print(f"HSHD_NUM=10 transactions: {cur.fetchone()[0]}")

cur.execute(
    "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='households' ORDER BY ORDINAL_POSITION"
)
print("\nhouseholds columns:", list(cur.fetchall()))
cur.execute(
    "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='products' ORDER BY ORDINAL_POSITION"
)
print("\nproducts columns:", list(cur.fetchall()))
cur.execute(
    "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='transactions' ORDER BY ORDINAL_POSITION"
)
print("\ntransactions columns:", list(cur.fetchall()))

conn.close()
