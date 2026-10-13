# F1 1:43 Model Catalog App

Static local MVP for the F1 1:43 model catalog and collection comparison interface.

The main project document is:

```text
../F1_143_MODEL_CATALOG_PROJECT.md
```

## Run Locally

Generate or provide `app/data/app-data.json`, then run:

```powershell
python app/serve_app.py
```

Open:

```text
http://127.0.0.1:4173/#/collection
```

## Rebuild App Data

```powershell
python app/scripts/prepare_app_data.py
```

## Refresh the Cloud Collection

In the app's `Doplnit ročník` tab, enter the admin token and choose **Načíst změny ze sbírky**. Select the current `Diecast 2026.xlsx` from a locally synchronized OneDrive folder. The server checks the `Overview` sheet, backs up the existing collection and app data, then rematches and rebuilds the app data.

For direct publishing from the synchronized OneDrive file, configure the admin token once in Windows and run the local helper:

```powershell
python app/scripts/publish_collection.py --configure
python app/scripts/publish_collection.py --publish
```

The helper stores the token encrypted with Windows DPAPI for the current Windows account. Codex can run the publish command after the workbook changes.

The current Hetzner endpoint uses HTTP, so the admin token is not encrypted while sent over the network. Use this only on a trusted network; configure HTTPS before relying on this for routine use over the public internet.

## Photo Discovery

```powershell
python app/scripts/discover_model_photos.py --season 1980 --limit 120
python app/scripts/prepare_app_data.py
```

## Public Repository Note

Generated JSON data and scraped caches are ignored in the public repository. Use sanitized sample data or regenerate private data locally.

