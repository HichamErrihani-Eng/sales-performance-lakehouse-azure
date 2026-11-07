# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Bronze → Silver : taux de change (API Frankfurter / BCE)
# MAGIC
# MAGIC L'API renvoie `{"base":"USD","rates":{"2008-01-02":{"EUR":0.68,...},...}}`.
# MAGIC La BCE ne publie pas de taux le week-end et les jours fériés : on **complète chaque jour**
# MAGIC avec le dernier taux connu, pour que chaque commande trouve un taux.
# MAGIC
# MAGIC Sens du taux : `taux` = nombre d'unités de `devise` pour 1 USD.

# COMMAND ----------

# MAGIC %run ./00_common

# COMMAND ----------

from pyspark.sql.types import MapType, StringType, DoubleType, StructType, StructField

schema = StructType([
    StructField("base", StringType()),
    StructField("rates", MapType(StringType(), MapType(StringType(), DoubleType()))),
])

raw = spark.read.text(f"{BRONZE}/api/frankfurter", wholetext=True)
# Data Factory ecrit le JSON avec un BOM UTF-8 : on le retire avant le parsing.
parsed = raw.select(F.from_json(F.regexp_replace("value", "^\\uFEFF", ""), schema).alias("j"), "load_date")
print("fichiers lus :", raw.count(), "| JSON valides :", parsed.filter("j is not null").count())

rates = (parsed
    .select("j.base", "load_date", F.explode("j.rates").alias("date_taux", "taux_par_devise"))
    .select("base", "load_date", F.to_date("date_taux").alias("date_taux"),
            F.explode("taux_par_devise").alias("devise", "taux")))

# Qualité : taux absent ou négatif
bad = rates.filter(F.col("taux").isNull() | (F.col("taux") <= 0) | F.col("date_taux").isNull())
rejected = write_rejects(bad, "api_frankfurter", "taux invalide", max_load(rates))
is_bad = F.col("taux").isNull() | (F.col("taux") <= 0) | F.col("date_taux").isNull()
rates = keep_latest(rates.filter(~is_bad), ["date_taux", "devise"], "load_date")

# COMMAND ----------

# Calendrier quotidien complet + report du dernier taux connu (forward fill)
bounds = rates.agg(F.min("date_taux").alias("d0"), F.max("date_taux").alias("d1"))
calendar = (bounds
    .select(F.explode(F.sequence("d0", "d1")).alias("date_taux"))
    .crossJoin(rates.select("devise").distinct()))

w = (Window.partitionBy("devise").orderBy("date_taux")
     .rowsBetween(Window.unboundedPreceding, 0))

daily = (calendar
    .join(rates.select("date_taux", "devise", "taux"), ["date_taux", "devise"], "left")
    .withColumn("taux_publie", F.col("taux").isNotNull())
    .withColumn("taux", F.last("taux", ignorenulls=True).over(w))
    .withColumn("base", F.lit("USD"))
    .filter(F.col("taux").isNotNull()))

info = merge_into(daily, f"{CATALOG}.silver.taux_change", ["date_taux", "devise"])
info["rejets"] = rejected
print(info)

# COMMAND ----------

display(spark.table(f"{CATALOG}.silver.taux_change").filter("devise = 'EUR'").orderBy("date_taux").limit(20))
