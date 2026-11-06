# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Bronze → Silver : tables SQL Server (AdventureWorksLT)
# MAGIC
# MAGIC Pour chaque table : lecture des fichiers Parquet de Bronze, contrôle des clés,
# MAGIC dédoublonnage (version la plus récente par `ModifiedDate`), puis **MERGE** dans Silver.
# MAGIC Relancer ce notebook ne crée jamais de doublons (idempotent).

# COMMAND ----------

# MAGIC %run ./00_common

# COMMAND ----------

# table source -> (table silver, clés primaires)
TABLES = {
    "SalesOrderHeader": ("sales_order_header", ["SalesOrderID"]),
    "SalesOrderDetail": ("sales_order_detail", ["SalesOrderDetailID"]),
    "Customer":         ("customer",           ["CustomerID"]),
    "CustomerAddress":  ("customer_address",   ["CustomerID", "AddressID"]),
    "Address":          ("address",            ["AddressID"]),
    "Product":          ("product",            ["ProductID"]),
    "ProductCategory":  ("product_category",   ["ProductCategoryID"]),
}

# Colonnes binaires inutiles pour l'analyse (images produits)
DROP_COLS = ["ThumbNailPhoto", "rowguid", "PasswordHash", "PasswordSalt"]

# COMMAND ----------

results = []
for source_table, (silver_table, keys) in TABLES.items():
    path = f"{BRONZE}/sqlserver/SalesLT/{source_table}"
    try:
        raw = spark.read.parquet(path)          # la colonne load_date vient des dossiers load_date=...
    except Exception as e:
        print(f"[{source_table}] aucun fichier en Bronze : {e}")
        continue

    raw = raw.drop(*[c for c in DROP_COLS if c in raw.columns])

    # 1) Qualité : une clé vide est rejetée
    null_key = " OR ".join([f"`{k}` IS NULL" for k in keys])
    rejected = write_rejects(raw.filter(null_key), source_table, "clé primaire vide", max_load(raw))
    valid = raw.filter(f"NOT ({null_key})")

    # 2) Dédoublonnage : la dernière version de chaque ligne
    latest = keep_latest(valid, keys, "ModifiedDate").drop("load_date")

    # 3) MERGE : mise à jour seulement si la source est plus récente
    info = merge_into(latest, f"{CATALOG}.silver.{silver_table}", keys,
                      update_condition="s.ModifiedDate > t.ModifiedDate")
    info["rejets"] = rejected
    results.append(info)
    print(info)

# COMMAND ----------

display(spark.createDataFrame(results)) if results else print("Rien à traiter")
