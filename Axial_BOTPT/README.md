# Seafloor Pressure Dashboard (GitHub Pages + Actions)

This repo turns `.dat` files under `data/raw/` into a simple web dashboard.

## How it works
- Put your files under `data/raw/<Station>/<Subgroup>/.../*.dat`
- GitHub Actions runs `parse_and_build.py` to generate `site/data/all_series.json`
- `site/index.html` reads the JSON and plots with Plotly
- Deployed automatically to GitHub Pages

## Quick start
1. Upload this repo to GitHub (all folders and files).
2. In your repo: **Settings → Pages → Build and deployment: GitHub Actions**.
3. Push/Upload — the workflow builds and deploys.
4. Add more `.dat` files under `data/raw/...` and push again.

### Units
If your raw values are **psi**, keep `ASSUME_UNITS = "psi"` (default).
If your raw values are already **kPa**, change it to `"kPa"`.
