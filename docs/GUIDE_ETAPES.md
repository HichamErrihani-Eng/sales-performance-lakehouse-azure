# Guide de déploiement pas à pas

Durée : 2 à 3 semaines à ton rythme. Fais une étape, vérifie le point de contrôle ✅, puis passe à la suivante.

Dans tout le guide, remplace :
| Repère | Exemple |
| --- | --- |
| `sql-hicham-sales` | `sql-hicham-demo` |
| `sthichamsales` | `sthichamdemo` (minuscules et chiffres, unique dans Azure) |
| `kv-hicham-sales` | `kv-hicham-demo` |
| `<NOM-WORKSPACE>` | `adb-hicham-demo` |

---

## Étape 0 — Prérequis
- Un abonnement Azure : https://azure.microsoft.com/free
- **Azure Databricks en niveau Premium** (essai gratuit de 14 jours possible). Unity Catalog et l'appel depuis Data Factory ne fonctionnent pas avec Databricks Free Edition.
- Un compte GitHub.
- Power BI Desktop (gratuit, Windows).

## Étape 1 — Groupe de ressources et base SQL
1. Portail Azure → **Groupes de ressources** → **Créer** → `rg_sales_lakehouse`, région `France Central`.
2. **SQL databases** → **Créer** :
   - Base : `sqldb-adventureworks` ; nouveau serveur `sql-hicham-sales`, authentification SQL, utilisateur `sqladmin`.
   - Calcul : **Basic**.
   - Mise en réseau : point de terminaison public, *Autoriser les services Azure* = Oui, *Ajouter l'IP actuelle* = Oui.
   - Paramètres supplémentaires : *Utiliser des données existantes* = **Exemple**.
3. Base → **Éditeur de requêtes** → exécuter dans l'ordre :
   - `sql/04_optionnel_etaler_dates_2008.sql` (recommandé : répartit les commandes sur 2008)
   - `sql/01_control_table.sql`
   - `sql/02_update_watermark_proc.sql`

✅ `SELECT * FROM etl.ControlTable;` renvoie 7 lignes.

## Étape 2 — Data Lake (ADLS Gen2)
1. **Comptes de stockage** → **Créer** → nom `sthichamsales`, redondance **LRS**.
   Onglet *Avancé* : cocher **Activer l'espace de noms hiérarchique** (c'est ce qui en fait un ADLS Gen2).
2. Dans le compte → **Conteneurs** → créer `landing`, `bronze`, `lakehouse`.
3. Dans `landing`, créer le dossier `objectifs` et y téléverser `data/objectifs_ventes_2008.csv`.

✅ Le fichier est visible dans `landing/objectifs/`.

## Étape 3 — Key Vault
1. **Coffres de clés** → **Créer** → `kv-hicham-sales`, modèle d'autorisation **RBAC Azure**.
2. Te donner le rôle **Key Vault Secrets Officer** sur le coffre (Contrôle d'accès IAM).
3. **Secrets** → **Générer/Importer** → nom `sql-admin-password`, valeur = mot de passe de `sqladmin`.

✅ Le secret apparaît, statut *Activé*.

## Étape 4 — Data Factory
1. **Data factories** → **Créer** → `adf-hicham-demo`, même groupe de ressources.
2. Donner des droits à **l'identité managée** de Data Factory (IAM → Ajouter une attribution de rôle) :
   - Key Vault : **Key Vault Secrets User**
   - Compte de stockage : **Storage Blob Data Contributor**
3. Publier ce dépôt sur ton GitHub, puis dans **ADF Studio** → **Gérer** → **Configuration Git** :
   - Type : GitHub, ton dépôt, branche `main`, **dossier racine `/adf`**.
   - ADF charge automatiquement les linked services, datasets, pipelines et le déclencheur.
4. Dans **Gérer → Services liés**, remplacer les repères `<...>` dans `ls_keyvault`, `ls_azuresql`, `ls_adls`. Cliquer **Tester la connexion** pour chacun.

✅ Les tests de connexion SQL, stockage et REST sont verts.

## Étape 5 — Premier chargement vers Bronze
Dans **Créer**, lancer avec **Déboguer**, l'un après l'autre :
1. `pl_sql_to_bronze` → 7 copies en parallèle.
2. `pl_csv_to_bronze`
3. `pl_api_fx_to_bronze` (paramètres par défaut : 2008-01-01 à 2008-12-31)

✅ Dans le conteneur `bronze` : dossiers `sqlserver/SalesLT/...`, `csv/objectifs/...`, `api/frankfurter/...`, chacun avec `load_date=AAAA-MM-JJ`.
✅ `SELECT SourceTable, LastWatermark, LastRowsCopied FROM etl.ControlTable;` montre des watermarks à jour.

## Étape 6 — Databricks et Unity Catalog
1. **Azure Databricks** → **Créer** → `<NOM-WORKSPACE>`, niveau **Premium**.
2. **Access Connector for Azure Databricks** → **Créer** → `ac-hicham-demo`.
   Sur le compte de stockage, donner à ce connecteur le rôle **Storage Blob Data Contributor**.
3. Dans Databricks → **Catalog** → **External data** :
   - **Credentials** → créer une *storage credential* avec l'ID de ressource du connecteur.
   - **External locations** → créer `loc_bronze` → `abfss://bronze@sthichamsales.dfs.core.windows.net/`
     et `loc_lakehouse` → `abfss://lakehouse@sthichamsales.dfs.core.windows.net/`.
4. **Compute** → créer un cluster : mode *Single user*, 1 worker (ou *Single node*), **arrêt automatique 20 min**.
5. **Workspace** → **Create → Git folder** → coller l'URL de ton dépôt GitHub.
6. Ouvrir `databricks/00_setup` → renseigner `storage_account` → **Run all**.
   Si la création du catalogue demande un emplacement, renseigner `managed_location` = `abfss://lakehouse@sthichamsales.dfs.core.windows.net/sales_demo`.
7. Exécuter à la main, dans l'ordre : `01`, `02`, `03`, `04`, `05`.

✅ Catalog Explorer montre `sales_demo.silver` (9 tables), `sales_demo.gold` (2 tables), `sales_demo.ops`.
✅ Le notebook `05` affiche tous les contrôles bloquants en **OK**.

## Étape 7 — Orchestration complète
1. Donner à l'identité managée de Data Factory le rôle **Contributor** sur le workspace Databricks.
2. Dans `ls_databricks` : renseigner domaine, ID de ressource du workspace et **ID du cluster** (Compute → cluster → URL ou onglet *Advanced*).
3. Dans `pl_transform_databricks`, mettre le bon `notebook_root` (chemin du Git folder) et `storage_account`.
4. Lancer `pl_master` en **Déboguer**.
5. **Publier**, puis **Gérer → Déclencheurs** → démarrer `tr_daily_0600`.

✅ `pl_master` termine en *Réussi*, avec les 3 ingestions en parallèle puis la transformation.

## Étape 8 — Prouver l'incrémental
1. Exécuter `sql/03_test_incremental.sql` (modifie 2 commandes).
2. Relancer `pl_master`.

✅ `LastRowsCopied` = **2** pour `SalesOrderHeader`, 0 pour les tables non modifiées.
✅ En Silver, les 2 commandes ont le nouveau `Freight`, et toujours **une seule ligne** par commande.

Fais une capture d'écran de ces deux résultats : c'est la meilleure preuve à montrer en entretien.

## Étape 9 — Power BI
Suivre `powerbi/mesures_dax.md` : connexion à un SQL Warehouse Databricks, tables Gold, mesures DAX, 3 pages.

✅ Le tableau de bord montre ventes, objectifs et taux d'atteinte par mois et par pays.

## Étape 10 — Publier et nettoyer
1. Ajouter dans le dépôt un dossier `images/` : schéma, run réussi de `pl_master`, tables Silver/Gold, tableau de bord.
2. Enregistrer une vidéo de 2 minutes qui parcourt le pipeline (lien dans le README).
3. Arrêter le cluster, désactiver le déclencheur.
4. Quand le projet est documenté : **supprimer le groupe de ressources** pour ne plus rien payer.

---

## Dépannage rapide
| Problème | Cause probable | Solution |
| --- | --- | --- |
| Test SQL refusé | Pare-feu du serveur | Serveur SQL → Mise en réseau → ajouter ton IP, autoriser les services Azure |
| `Forbidden` sur le stockage | Rôle manquant | Storage Blob Data Contributor pour ADF (ou le connecteur Databricks) ; attendre 5 min |
| Key Vault refusé | Rôle manquant | Key Vault Secrets User pour l'identité de Data Factory |
| `PATH_NOT_FOUND` dans Databricks | External location absente | Créer `loc_bronze` à l'étape 6 |
| Commandes sans taux EUR (contrôle 05) | Dates hors de la période API | Relancer `pl_api_fx_to_bronze` avec les bonnes dates |
