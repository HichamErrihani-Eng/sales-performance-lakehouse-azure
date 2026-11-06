/* =====================================================================
   Table de contrôle du pipeline piloté par métadonnées
   À exécuter dans la base Azure SQL qui contient AdventureWorksLT.
   Chaque ligne = une table source à charger en Bronze.
   ===================================================================== */

IF SCHEMA_ID('etl') IS NULL
    EXEC('CREATE SCHEMA etl');
GO

IF OBJECT_ID('etl.ControlTable') IS NOT NULL
    DROP TABLE etl.ControlTable;
GO

CREATE TABLE etl.ControlTable (
    Id               INT IDENTITY(1,1) PRIMARY KEY,
    SourceSchema     SYSNAME       NOT NULL,
    SourceTable      SYSNAME       NOT NULL,
    WatermarkColumn  SYSNAME       NOT NULL,   -- colonne de date de modification
    LastWatermark    DATETIME2(3)  NOT NULL DEFAULT '1900-01-01',
    BronzeFolder     NVARCHAR(200) NOT NULL,   -- dossier cible dans le conteneur bronze
    IsActive         BIT           NOT NULL DEFAULT 1,
    LastRunUtc       DATETIME2(3)  NULL,
    LastRowsCopied   INT           NULL
);
GO

/* Toutes les tables AdventureWorksLT ont une colonne ModifiedDate.
   Premier chargement : LastWatermark = 1900-01-01, donc tout est copié.
   Chargements suivants : seules les lignes modifiées depuis sont copiées. */
INSERT INTO etl.ControlTable (SourceSchema, SourceTable, WatermarkColumn, BronzeFolder)
VALUES
    ('SalesLT', 'SalesOrderHeader', 'ModifiedDate', 'sqlserver/SalesLT/SalesOrderHeader'),
    ('SalesLT', 'SalesOrderDetail', 'ModifiedDate', 'sqlserver/SalesLT/SalesOrderDetail'),
    ('SalesLT', 'Customer',         'ModifiedDate', 'sqlserver/SalesLT/Customer'),
    ('SalesLT', 'CustomerAddress',  'ModifiedDate', 'sqlserver/SalesLT/CustomerAddress'),
    ('SalesLT', 'Address',          'ModifiedDate', 'sqlserver/SalesLT/Address'),
    ('SalesLT', 'Product',          'ModifiedDate', 'sqlserver/SalesLT/Product'),
    ('SalesLT', 'ProductCategory',  'ModifiedDate', 'sqlserver/SalesLT/ProductCategory');
GO

SELECT * FROM etl.ControlTable;
