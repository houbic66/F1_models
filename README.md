# F1 1:43 Model Catalog

Public source repository for a Formula 1 1:43 model catalog and collection comparison app.

The project separates two concepts:

- **Master catalog**: an independent catalog of manufactured F1 1:43 models, collected from manufacturers, specialist shops, stocklists, auctions, and forums.
- **Collection comparison**: a later matching step against a private collection workbook.

The private collection workbook is not a source of truth for which models exist. It is used only after the independent master catalog has been built.

## Current Status

This is a local MVP/static web app with import and data-preparation scripts. The app can show:

- collection rows by season,
- model detail with main photo and thumbnails,
- master catalog rows,
- candidate records that need verification,
- row coloring for owned/missing/no-model states,
- year-specific sorting and filtering.

The repository is prepared for public GitHub use. Private workbooks, generated JSON data, scraped caches, and local outputs are ignored by `.gitignore`.

## Project Notes

The living project document is:

```text
F1_143_MODEL_CATALOG_PROJECT.md
```

It contains the import rules, manufacturer code rules, photo rules, lessons learned, UI logic, and cloud migration plan.

## Local App

The static app is in:

```text
app/
```

To run it locally after generating data:

```powershell
python app/serve_app.py
```

Then open:

```text
http://127.0.0.1:4173/#/collection
```

## Hetzner Deployment

Deployment notes for a clean Hetzner VPS are in:

```text
deploy/hetzner/README.md
```

## Data Policy

The following are intentionally not committed to the public repository:

- personal collection workbooks,
- generated audit outputs,
- generated `app-data.json`,
- photo override JSON with collected links,
- scraped page cache,
- local temporary files.

For a public demo or cloud deployment, create a sanitized sample dataset or connect the app to a backend/database.

## Important Rules

- Build the master catalog independently first.
- Compare against the private collection only at the end.
- Spark canonical codes must be `S` plus four digits.
- Minichamps canonical codes must be nine digits.
- Seller codes such as Raceland codes are source references, not manufacturer catalog codes.
- A photo is valid only after the URL is checked and returns an image.
- Non-F1 entries such as F2, F3, Formula Ford, IndyCar, Le Mans, GT, DTM, and similar categories must be filtered out.

## Next Development Steps

- Create a single `build_year.py` yearly import pipeline.
- Add an official Minichamps importer.
- Automate Spark photo fallback when the official CDN returns `403`.
- Generate per-year audit reports.
- Add backend/database storage for cloud use.
- Add sanitized public sample data for GitHub demo deployment.
