/* =====================================================================
   OPTIONNEL — Données de démonstration
   Dans AdventureWorksLT, toutes les commandes ont la même date
   (1er juin 2008). Ce script répartit les commandes sur l'année 2008
   pour obtenir un tableau de bord mensuel plus parlant.
   À lancer UNE FOIS, avant le premier run du pipeline.
   Les dates restent cohérentes : ShipDate = OrderDate + 7 jours,
   DueDate = OrderDate + 12 jours.
   ===================================================================== */

UPDATE SalesLT.SalesOrderHeader
SET OrderDate    = DATEADD(DAY, -((SalesOrderID * 37) % 330), CAST('2008-12-20' AS DATETIME)),
    ShipDate     = DATEADD(DAY, 7,  DATEADD(DAY, -((SalesOrderID * 37) % 330), CAST('2008-12-20' AS DATETIME))),
    DueDate      = DATEADD(DAY, 12, DATEADD(DAY, -((SalesOrderID * 37) % 330), CAST('2008-12-20' AS DATETIME))),
    ModifiedDate = SYSUTCDATETIME();

-- Vérification : nombre de commandes par mois
SELECT FORMAT(OrderDate, 'yyyy-MM') AS mois, COUNT(*) AS nb_commandes
FROM SalesLT.SalesOrderHeader
GROUP BY FORMAT(OrderDate, 'yyyy-MM')
ORDER BY mois;
