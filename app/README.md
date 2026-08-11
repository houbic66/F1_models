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

## Photo Discovery

```powershell
python app/scripts/discover_model_photos.py --season 1980 --limit 120
python app/scripts/prepare_app_data.py
```

## Public Repository Note

Generated JSON data and scraped caches are ignored in the public repository. Use sanitized sample data or regenerate private data locally.

