# Databricks notebook source
# MAGIC %md
# MAGIC # 00 — Mise en place (à exécuter une seule fois)
# MAGIC
# MAGIC Ce notebook crée le catalogue Unity Catalog, les schémas `silver` et `gold`,
# MAGIC et vérifie l'accès au conteneur `bronze` du Data Lake.
# MAGIC
# MAGIC **Prérequis (voir docs/GUIDE_ETAPES.md, étape 6) :**
# MAGIC 1. Un *Access Connector for Azure Databricks* avec le rôle *Storage Blob Data Contributor* sur le compte de stockage.
# MAGIC 2. Une *storage credential* et une *external location* Unity Catalog sur `abfss://bronze@<stockage>.dfs.core.windows.net/`.

# COMMAND ----------

dbutils.widgets.text("storage_account", "sthichamsales")
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("bronze_path", "/Volumes/workspace/default/raw/bronze")
# Laisser vide si le metastore a un stockage par défaut.
# Sinon : abfss://lakehouse@sthichamsales.dfs.core.windows.net/sales_demo (external location requise)
dbutils.widgets.text("managed_location", "")

storage_account = dbutils.widgets.get("storage_account")
catalog = dbutils.widgets.get("catalog")
managed_location = dbutils.widgets.get("managed_location").strip()

# COMMAND ----------

if catalog != "workspace":   # "workspace" existe deja (Free Edition)
    if managed_location:
        spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog} MANAGED LOCATION '{managed_location}'")
    else:
        spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.silver COMMENT 'Données nettoyées et dédoublonnées'")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.gold COMMENT 'Tables métier prêtes pour Power BI'")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.ops COMMENT 'Rejets et journal qualité'")

# COMMAND ----------

# Test d'accès au conteneur bronze (doit lister les dossiers sqlserver, api, csv après le premier run ADF)
bronze_root = (dbutils.widgets.get("bronze_path").strip()
               or f"abfss://bronze@{storage_account}.dfs.core.windows.net/")
display(dbutils.fs.ls(bronze_root))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Droits pour Power BI (optionnel)
# MAGIC Donner la lecture du schéma `gold` à un groupe d'utilisateurs :
# MAGIC ```sql
# MAGIC GRANT USE CATALOG ON CATALOG sales_demo TO `analystes`;
# MAGIC GRANT USE SCHEMA, SELECT ON SCHEMA sales_demo.gold TO `analystes`;
# MAGIC ```
