import os
import mssql_python

server = os.environ["SQL_SERVER"] + ".database.windows.net"

conn = mssql_python.connect(
    server=server,
    database=os.environ["SQL_DB"],
    uid=os.environ["SQL_ADMIN"],
    pwd=os.environ["SQL_PASSWORD"],
    encrypt="yes",
    trustservercertificate="no"
)

cursor = conn.cursor()
cursor.execute("SELECT DB_NAME(), @@VERSION")
row = cursor.fetchone()

print("Connected to database:", row[0])
print("SQL Server:", str(row[1]).splitlines()[0])

conn.close()
