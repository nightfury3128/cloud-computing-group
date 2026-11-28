-- App users: separate from source data tables. Never store plaintext passwords.
IF OBJECT_ID('dbo.app_users', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.app_users (
        id            INT IDENTITY(1,1) PRIMARY KEY,
        username      NVARCHAR(64)  NOT NULL UNIQUE,
        email         NVARCHAR(254) NOT NULL UNIQUE,
        password_hash NVARCHAR(255) NOT NULL,
        created_at    DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

-- Helpful indexes for the join-heavy household queries.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_transactions_HSHD_NUM' AND object_id = OBJECT_ID('dbo.transactions'))
    CREATE INDEX IX_transactions_HSHD_NUM ON dbo.transactions (HSHD_NUM);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_transactions_PRODUCT_NUM' AND object_id = OBJECT_ID('dbo.transactions'))
    CREATE INDEX IX_transactions_PRODUCT_NUM ON dbo.transactions (PRODUCT_NUM);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_transactions_DATE' AND object_id = OBJECT_ID('dbo.transactions'))
    CREATE INDEX IX_transactions_DATE ON dbo.transactions ([DATE]);
GO
