# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Bronze → Silver : objectifs de ventes (CSV)
# MAGIC
# MAGIC Format attendu : `mois` (AAAA-MM), `pays`, `objectif_eur`.
# MAGIC Les lignes invalides vont dans `ops.rejets`. Le fichier le plus récent gagne.

# COMMAND ----------

# MAGIC %run ./00_common

# COMMAND ----------

PAYS_VALIDES = ["United States", "Canada", "United Kingdom"]

raw = (spark.read.option("header", True).option("encoding", "UTF-8")
       .csv(f"{BRONZE}/csv/objectifs"))          # partition load_date découverte automatiquement

clean = (raw
    .withColumn("mois", F.trim("mois"))
    .withColumn("pays", F.initcap(F.trim("pays")))
    .withColumn("objectif_eur", F.col("objectif_eur").cast("decimal(18,2)"))
    .withColumn("load_date", F.col("load_date").cast("string")))

# Règles de qualité
is_valid = (F.col("mois").rlike(r"^\d{4}-(0[1-9]|1[0-2])$")
            & F.col("pays").isin(PAYS_VALIDES)
            & F.col("objectif_eur").isNotNull()
            & (F.col("objectif_eur") > 0))

rejected = write_rejects(clean.filter(~is_valid), "objectifs_csv",
                         "mois, pays ou objectif invalide", max_load(clean))
valid = keep_latest(clean.filter(is_valid), ["mois", "pays"], "load_date").drop("load_date")

info = merge_into(valid, f"{CATALOG}.silver.objectifs_ventes", ["mois", "pays"])
info["rejets"] = rejected
print(info)

# COMMAND ----------

display(spark.table(f"{CATALOG}.silver.objectifs_ventes").orderBy("mois", "pays"))
