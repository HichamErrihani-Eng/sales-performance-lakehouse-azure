# Databricks notebook source
# MAGIC %md
# MAGIC # 05 — Contrôles qualité
# MAGIC
# MAGIC Chaque contrôle est écrit dans `ops.journal_qualite`.
# MAGIC Si un contrôle **bloquant** échoue, le notebook lève une erreur :
# MAGIC Data Factory marque alors le run en échec (et peut envoyer une alerte).

# COMMAND ----------

# MAGIC %run ./00_common

# COMMAND ----------

s = lambda t: spark.table(f"{CATALOG}.silver.{t}")
g = lambda t: spark.table(f"{CATALOG}.gold.{t}")
checks = []

def check(nom, valeur, ok, bloquant):
    checks.append((nom, str(valeur), "OK" if ok else "ECHEC", bloquant))

# 1. Pas de doublon de clé en Silver
dup = s("sales_order_header").groupBy("SalesOrderID").count().filter("count > 1").count()
check("Doublons SalesOrderID en Silver", dup, dup == 0, True)

# 2. Chaque commande a un taux de change
orders = s("sales_order_header").select(F.to_date("OrderDate").alias("d"))
eur = s("taux_change").filter("devise = 'EUR'").select(F.col("date_taux").alias("d"))
sans_taux = orders.join(eur, "d", "left_anti").count()
check("Commandes sans taux EUR", sans_taux, sans_taux == 0, True)

# 3. Chaque commande a un pays
sans_pays = (s("sales_order_header").join(
    s("address").select(F.col("AddressID").alias("ShipToAddressID")), "ShipToAddressID", "left_anti").count())
check("Commandes sans adresse/pays", sans_pays, sans_pays == 0, False)

# 4. Le total Gold = le total Silver (pas de perte dans les jointures)
total_silver = s("sales_order_header").agg(F.sum("TotalDue")).first()[0] or 0
total_gold = g("ventes_vs_objectifs").agg(F.sum("ventes_usd")).first()[0] or 0
check("Total USD Silver = Gold", f"{total_silver} / {total_gold}",
      abs(float(total_silver) - float(total_gold)) < 0.05, True)

# 5. Ventes sans objectif (information pour le métier)
sans_obj = g("ventes_vs_objectifs").filter("objectif_eur IS NULL AND ventes_eur > 0").count()
check("Mois/pays vendus sans objectif", sans_obj, sans_obj == 0, False)

# 6. Rejets du run
rejets = (spark.table(f"{CATALOG}.ops.rejets").filter(F.to_date("run_ts") == F.current_date()).count()
          if spark.catalog.tableExists(f"{CATALOG}.ops.rejets") else 0)
check("Lignes rejetées aujourd'hui", rejets, rejets == 0, False)

# COMMAND ----------

journal = (spark.createDataFrame(checks, "controle string, valeur string, statut string, bloquant boolean")
           .withColumn("run_ts", F.lit(RUN_TS)))
journal.write.format("delta").mode("append").saveAsTable(f"{CATALOG}.ops.journal_qualite")
display(journal)

echecs = [c for c in checks if c[2] == "ECHEC" and c[3]]
if echecs:
    raise Exception(f"Contrôles qualité bloquants en échec : {[c[0] for c in echecs]}")
