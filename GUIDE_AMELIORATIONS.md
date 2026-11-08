# Ajouter les 3 améliorations au dépôt

Copier ces dossiers à la racine du dépôt `sales-performance-lakehouse-azure` :

| Dossier / fichier | Rôle |
| --- | --- |
| `src/transforms.py` | Logique de transformation testable (dédoublonnage, rejets, report du taux, taux d'atteinte) |
| `tests/` + `requirements-dev.txt` | 5 tests pytest exécutés en local avec Spark |
| `infra/main.bicep` + `main.parameters.json` | Infrastructure en code : SQL gratuit, Data Lake, Key Vault, Data Factory, rôles RBAC |
| `.github/workflows/ci.yml` | CI GitHub Actions : tests, validation des JSON ADF, compilation Bicep, à chaque push |

## Sur la VM Ubuntu
```
cd ~/projets/azure-sales-pipeline
git pull
unzip -o ~/Downloads/ameliorations.zip -d .
pip install -r requirements-dev.txt --break-system-packages
pytest -v tests
git add -A
git commit -m "Add unit tests, Bicep infrastructure and CI pipeline"
git push
```
Java 17 doit être installé pour PySpark : `sudo apt install -y openjdk-17-jre-headless`.

## Vérifier sur GitHub
Onglet **Actions** : le workflow **CI** doit être vert (3 jobs).

## Déployer l'infrastructure (facultatif)
```
az deployment group create -g rg_sales_lakehouse -f infra/main.bicep -p infra/main.parameters.json -p sqlAdminPassword='<mot de passe>'
```
`adminObjectId` : `az ad signed-in-user show --query id -o tsv`.
Déjà créées dans le portail ? Le déploiement les met en conformité avec le fichier (idempotent).
