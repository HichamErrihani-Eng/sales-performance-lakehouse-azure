from datetime import date

from pyspark.sql import functions as F

from src.transforms import forward_fill_rates, keep_latest, split_valid_rejected, taux_atteinte


def test_keep_latest_garde_la_version_la_plus_recente(spark):
    df = spark.createDataFrame(
        [(71774, 100.0, "2026-11-06"), (71774, 150.0, "2026-11-07"), (71776, 80.0, "2026-11-06")],
        ["SalesOrderID", "Freight", "load_date"])
    out = {r.SalesOrderID: r.Freight for r in keep_latest(df, ["SalesOrderID"], "load_date").collect()}
    assert out == {71774: 150.0, 71776: 80.0}


def test_keep_latest_est_idempotent(spark):
    df = spark.createDataFrame([(1, "a", 1), (1, "b", 2)], ["id", "v", "ts"])
    once = keep_latest(df, ["id"], "ts")
    twice = keep_latest(once, ["id"], "ts")
    assert once.collect() == twice.collect()


def test_split_valid_rejected_isole_les_cles_vides(spark):
    df = spark.createDataFrame([(1, "Canada"), (None, "Canada"), (3, "France")], ["id", "pays"])
    invalide = F.col("id").isNull() | ~F.col("pays").isin("Canada", "United States", "United Kingdom")
    valides, rejets = split_valid_rejected(df, invalide)
    assert valides.count() == 1 and rejets.count() == 2


def test_forward_fill_complete_le_week_end(spark):
    # Vendredi 4 et lundi 7 janvier 2008 publiés ; samedi 5 et dimanche 6 absents
    rates = spark.createDataFrame(
        [(date(2008, 1, 4), "EUR", 0.679), (date(2008, 1, 7), "EUR", 0.6792)],
        ["date_taux", "devise", "taux"])
    out = {r.date_taux: (r.taux, r.taux_publie) for r in forward_fill_rates(rates).collect()}
    assert len(out) == 4
    assert out[date(2008, 1, 5)] == (0.679, False)
    assert out[date(2008, 1, 6)] == (0.679, False)
    assert out[date(2008, 1, 7)] == (0.6792, True)


def test_taux_atteinte_sans_objectif_est_nul(spark):
    df = spark.createDataFrame([(500.0, 1000.0), (500.0, 0.0), (500.0, None)], "v double, o double")
    out = [r.t for r in df.select(taux_atteinte(F.col("v"), F.col("o")).alias("t")).collect()]
    assert out == [0.5, None, None]
