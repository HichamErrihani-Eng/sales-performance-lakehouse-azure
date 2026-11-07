# Databricks notebook source
# MAGIC %md
# MAGIC # 00 — Fonctions communes
# MAGIC Chargé par les autres notebooks avec `%run ./00_common`.

# COMMAND ----------

from datetime import datetime, timezone
from delta.tables import DeltaTable
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

dbutils.widgets.text("storage_account", "sthichamsales")
dbutils.widgets.text("catalog", "workspace")
# Chemin Bronze explicite (volume Databricks Free Edition). Vide = Data Lake Azure.
dbutils.widgets.text("bronze_path", "/Volumes/workspace/default/raw/bronze")

STORAGE_ACCOUNT = dbutils.widgets.get("storage_account")
CATALOG = dbutils.widgets.get("catalog")
BRONZE = (dbutils.widgets.get("bronze_path").strip().rstrip("/")
          or f"abfss://bronze@{STORAGE_ACCOUNT}.dfs.core.windows.net")
RUN_TS = datetime.now(timezone.utc)

# COMMAND ----------

def table_exists(full_name: str) -> bool:
    return spark.catalog.tableExists(full_name)


def merge_into(df: DataFrame, full_name: str, keys: list, update_condition: str = None) -> dict:
    """Upsert idempotent : met à jour si la clé existe, insère sinon.
    Crée la table Delta au premier passage."""
    df = df.withColumn("_silver_updated_at", F.lit(RUN_TS))
    if not table_exists(full_name):
        df.write.format("delta").saveAsTable(full_name)
        return {"table": full_name, "mode": "create", "rows": df.count()}

    cond = " AND ".join([f"t.`{k}` = s.`{k}`" for k in keys])
    (DeltaTable.forName(spark, full_name).alias("t")
        .merge(df.alias("s"), cond)
        .whenMatchedUpdateAll(condition=update_condition)
        .whenNotMatchedInsertAll()
        .execute())
    return {"table": full_name, "mode": "merge", "rows": df.count()}


def keep_latest(df: DataFrame, keys: list, order_col: str) -> DataFrame:
    """Dédoublonnage : garde la version la plus récente de chaque clé."""
    w = Window.partitionBy(*keys).orderBy(F.col(order_col).desc())
    return df.withColumn("_rn", F.row_number().over(w)).filter("_rn = 1").drop("_rn")


def max_load(df: DataFrame):
    """Date du dernier chargement Bronze (dossier load_date le plus récent)."""
    return df.agg(F.max("load_date")).first()[0]


def write_rejects(df: DataFrame, source: str, reason: str, last_load=None) -> int:
    """Met de côté les lignes invalides au lieu de bloquer le pipeline.
    Si last_load est fourni, seules les lignes de ce chargement sont journalisées
    (Bronze est relu en entier : on évite de rejeter deux fois la même ligne)."""
    if last_load is not None:
        df = df.filter(F.col("load_date") == last_load)
    n = df.count()
    if n > 0:
        (df.select(F.to_json(F.struct("*")).alias("ligne_json"))
           .withColumn("source", F.lit(source))
           .withColumn("raison", F.lit(reason))
           .withColumn("run_ts", F.lit(RUN_TS))
           .write.format("delta").mode("append").saveAsTable(f"{CATALOG}.ops.rejets"))
    return n
