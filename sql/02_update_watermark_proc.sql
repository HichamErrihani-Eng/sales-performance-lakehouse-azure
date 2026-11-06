/* =====================================================================
   Procédure appelée par Data Factory après chaque copie réussie.
   Elle enregistre le nouveau watermark et le nombre de lignes copiées.
   ===================================================================== */

CREATE OR ALTER PROCEDURE etl.usp_UpdateWatermark
    @Id            INT,
    @NewWatermark  DATETIME2(3),
    @RowsCopied    INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Si la table source était vide, MAX() renvoie NULL : on ne touche pas au watermark.
    UPDATE etl.ControlTable
    SET LastWatermark  = COALESCE(@NewWatermark, LastWatermark),
        LastRunUtc     = SYSUTCDATETIME(),
        LastRowsCopied = @RowsCopied
    WHERE Id = @Id;
END;
GO
