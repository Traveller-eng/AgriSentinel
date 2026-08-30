# AgriSentinel Integration Audit

Date: 2026-08-30

## Dependency Manifests

- Required for this repo: `requirements.txt`, `backend/requirements.txt`,
  `requirements-ml.txt`, and `ml/requirements.txt`.
- Not required: `package.json`. The app is a Python Streamlit app, not a Node,
  React, Express, or Next.js app.
- If a separate React frontend is added later, create `frontend/package.json` at
  that time and keep it separate from the current Streamlit MVP.

## Folder Check

- `backend/`: SQLAlchemy models, database operations, weather fetch/cache, risk
  scoring, and risk-engine tests.
- `data/`: JSON knowledge base for all five tomato classes.
- `frontend/design_reference/`: static design references only. Runtime frontend is
  currently `app.py` through Streamlit.
- `ml/`: labels, training script, prediction wrapper, Grad-CAM, and smoke tests.
- `ml/models/`: expected location for `tomato_mobilenetv2.keras`.
- `uploads/`: generated local uploads and demo placeholder files.

## Verified Integration Path

1. Farmer submits an image and metadata in `app.py`.
2. `app.py` calls `ml.predict.predict_with_gradcam()` when the trained model exists.
3. If TensorFlow/model is missing, `app.py` uses deterministic demo prediction.
4. `db_ops.insert_report()` validates inputs and writes a pending report.
5. `db_ops.evaluate_and_update_risk()` fetches weather, counts nearby confirmed
   cases, calls `risk_engine.compute_risk()`, and persists severity.
6. Extension buttons call `db_ops.update_report_status()`.
7. Official filters call `db_ops.get_reports_filtered()` and chart data comes from
   `db_ops.get_case_counts_by_day()`.

## Remaining Demo Risks

- Real model file is still required for actual ML inference:
  `ml/models/tomato_mobilenetv2.keras`.
- TensorFlow is intentionally isolated in `requirements-ml.txt` because it is large;
  the Streamlit demo can run without it using fallback mode.
- Weather API failures are handled with cache/default fallback, but live weather
  depends on internet access.
- `frontend/` is a reference folder, not a buildable JS app.
