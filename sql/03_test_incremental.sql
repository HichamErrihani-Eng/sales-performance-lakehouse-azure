/* =====================================================================
   Test du chargement incrémental (à lancer APRÈS un premier run complet).
   On modifie 2 commandes : au run suivant, seules ces 2 lignes
   doivent être copiées en Bronze, puis mises à jour par MERGE en Silver.
   ===================================================================== */

UPDATE SalesLT.SalesOrderHeader
SET Freight      = Freight + 10,
    ModifiedDate = SYSUTCDATETIME()
WHERE SalesOrderID IN (71774, 71776);

-- Vérifier les watermarks et le nombre de lignes du dernier run
SELECT SourceTable, LastWatermark, LastRunUtc, LastRowsCopied
FROM etl.ControlTable
ORDER BY Id;
