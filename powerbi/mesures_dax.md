# Power BI — connexion et mesures DAX

## Connexion
1. Power BI Desktop → **Obtenir des données** → **Azure Databricks**.
2. Renseigner le *Server hostname* et le *HTTP path* d'un **SQL Warehouse** (Databricks → SQL Warehouses → Connection details).
3. Mode **Import**. Choisir le catalogue `sales_demo`, schéma `gold` :
   - `ventes_vs_objectifs`
   - `ventes_par_categorie`

## Table de dates (Modélisation → Nouvelle table)
```DAX
Calendrier =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2008, 1, 1 ), DATE ( 2008, 12, 31 ) ),
    "Mois", FORMAT ( [Date], "yyyy-MM" ),
    "Libellé mois", FORMAT ( [Date], "mmm yyyy" ),
    "Trimestre", "T" & QUARTER ( [Date] )
)
```
Relation : `Calendrier[Mois]` (1) → `ventes_vs_objectifs[mois]` (plusieurs), filtrage dans un seul sens.
(Pour une relation sur une colonne texte non unique côté Calendrier, créer plutôt une table `Mois = DISTINCT(Calendrier[Mois])` et relier `Mois[Mois]`.)

## Mesures
```DAX
Ventes EUR = SUM ( ventes_vs_objectifs[ventes_eur] )

Objectif EUR = SUM ( ventes_vs_objectifs[objectif_eur] )

Taux d'atteinte = DIVIDE ( [Ventes EUR], [Objectif EUR] )

Écart EUR = [Ventes EUR] - [Objectif EUR]

Nb commandes = SUM ( ventes_vs_objectifs[nb_commandes] )

Panier moyen EUR = DIVIDE ( [Ventes EUR], [Nb commandes] )

Ventes EUR cumul = TOTALYTD ( [Ventes EUR], Calendrier[Date] )

Couleur atteinte =
SWITCH (
    TRUE (),
    [Taux d'atteinte] >= 1, "#1D9E75",
    [Taux d'atteinte] >= 0.8, "#EF9F27",
    "#E24B4A"
)
```

## Pages proposées
1. **Vue d'ensemble** : cartes Ventes EUR, Objectif EUR, Taux d'atteinte ; histogramme Ventes vs Objectif par mois.
2. **Par pays** : carte (map) par `pays`, tableau avec mise en forme conditionnelle sur `Couleur atteinte`.
3. **Par catégorie** : `ventes_par_categorie`, top catégories (barres), évolution mensuelle.
