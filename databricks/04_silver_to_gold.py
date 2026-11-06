# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — Silver → Gold : tables métier pour Power BI
# MAGIC
# MAGIC 1. `gold.ventes_vs_objectifs` : ventes par mois et par pays, converties en EUR, comparées aux objectifs.
# MAGIC 2. `gold.ventes_par_categorie` : ventes par mois et par catégorie de produit, en EUR.
# MAGIC
# MAGIC Les tables Gold sont petites et entièrement recalculées à chaque run (`overwrite`) :
# MAGIC c'est plus simple et toujours cohérent avec Silver.

# COMMAND ----------

# MAGIC %run ./00_common

# COMMAND ----------

s = lambda t: spark.table(f"{CATALOG}.silver.{t}")

orders = s("sales_order_header").select(
    "SalesOrderID", F.to_date("OrderDate").alias("date_commande"),
    "ShipToAddressID", F.col("TotalDue").cast("decimal(18,2)").alias("montant_usd"))

address = s("address").select(F.col("AddressID").alias("ShipToAddressID"),
                              F.col("CountryRegion").alias("pays"))

eur = s("taux_change").filter("devise = 'EUR'").select(
    F.col("date_taux").alias("date_commande"), F.col("taux").alias("taux_usd_eur"))

ventes = (orders
    .join(address, "ShipToAddressID", "left")
    .join(eur, "date_commande", "left")
    .withColumn("mois", F.date_format("date_commande", "yyyy-MM"))
    .withColumn("montant_eur", F.round(F.col("montant_usd") * F.col("taux_usd_eur"), 2)))

# COMMAND ----------

ventes_mois_pays = (ventes.groupBy("mois", "pays").agg(
    F.countDistinct("SalesOrderID").alias("nb_commandes"),
    F.round(F.sum("montant_usd"), 2).alias("ventes_usd"),
    F.round(F.sum("montant_eur"), 2).alias("ventes_eur")))

objectifs = s("objectifs_ventes").select("mois", "pays", "objectif_eur")

gold_vs = (ventes_mois_pays
    .join(objectifs, ["mois", "pays"], "full_outer")
    .fillna({"nb_commandes": 0, "ventes_usd": 0, "ventes_eur": 0})
    .withColumn("taux_atteinte",
        F.when(F.col("objectif_eur") > 0, F.round(F.col("ventes_eur") / F.col("objectif_eur"), 4)))
    .withColumn("ecart_eur", F.round(F.col("ventes_eur") - F.coalesce("objectif_eur", F.lit(0)), 2))
    .withColumn("_gold_updated_at", F.lit(RUN_TS)))

gold_vs.write.format("delta").mode("overwrite").option("overwriteSchema", True) \
    .saveAsTable(f"{CATALOG}.gold.ventes_vs_objectifs")

# COMMAND ----------

detail = s("sales_order_detail").select("SalesOrderID", "ProductID", "OrderQty",
                                        F.col("LineTotal").cast("decimal(18,2)").alias("ligne_usd"))
product = s("product").select("ProductID", "ProductCategoryID")
category = s("product_category").select(
    F.col("ProductCategoryID"), F.col("Name").alias("categorie"))

gold_cat = (detail
    .join(ventes.select("SalesOrderID", "mois", "taux_usd_eur"), "SalesOrderID", "inner")
    .join(product, "ProductID", "left")
    .join(category, "ProductCategoryID", "left")
    .groupBy("mois", "categorie").agg(
        F.sum("OrderQty").alias("quantite"),
        F.round(F.sum(F.col("ligne_usd") * F.col("taux_usd_eur")), 2).alias("ventes_eur"))
    .withColumn("_gold_updated_at", F.lit(RUN_TS)))

gold_cat.write.format("delta").mode("overwrite").option("overwriteSchema", True) \
    .saveAsTable(f"{CATALOG}.gold.ventes_par_categorie")

# COMMAND ----------

display(spark.table(f"{CATALOG}.gold.ventes_vs_objectifs").orderBy("mois", "pays"))
