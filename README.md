# AgriSentinel

AI-Powered Crop Health Detection, Risk Forecasting and Early-Warning Platform.

This is a Streamlit MVP for SIH26131. It intentionally uses one Python app
instead of a separate JavaScript frontend and API backend, so a `package.json`
file is not required. Runtime dependencies live in `requirements.txt`, and the
optional ML training/inference dependencies live in `requirements-ml.txt`.

## What Is Built

- Farmer flow: tomato leaf upload, growth-stage selection, diagnosis, confidence,
  weather-aware risk score, checklist, and advisory.
- Extension flow: risk-sorted report queue, report detail view, confirm/reject/send
  to lab workflow, and pest-trap observation entry.
- Official flow: confirmed-case map, district/disease/date filters, metrics, table,
  and trend chart.
- Backend: SQLite via SQLAlchemy, Open-Meteo weather cache, rule-based risk engine,
  and validated database write helpers.
- ML package: MobileNetV2 training script, prediction wrapper, Grad-CAM helper, and
  tests. The app falls back to deterministic demo predictions until the trained
  model file is copied into place.

## Project Layout

```text
AgriSentinel/
  app.py                       Streamlit UI for all three roles
  backend/                     Database models, DB operations, weather, risk logic
  data/knowledge_base.json      Disease advisory content
  frontend/design_reference/    Static design reference screenshots/tokens
  ml/                          Training, prediction, labels, Grad-CAM
  ml/models/                   Put tomato_mobilenetv2.keras here after Colab training
  seed_demo_data.py            Generates disclosed simulated Maharashtra reports
  requirements.txt             App/runtime dependencies
  requirements-ml.txt          App plus TensorFlow ML dependencies
```

## Setup

Use Python 3.10 or newer.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python seed_demo_data.py --reset --count 40
python -m streamlit run app.py --server.port 8501
```

Open `http://localhost:8501`.

For real model inference, train with `ml/train.py` in Colab, then copy the exported
file to:

```text
ml/models/tomato_mobilenetv2.keras
```

Install ML dependencies only on the machine/session that needs TensorFlow:

```powershell
python -m pip install -r requirements-ml.txt
```

## Verification

```powershell
python -m pytest backend\test_risk_engine.py ml\test_predict.py -q
python -m py_compile app.py seed_demo_data.py backend\models.py backend\db_ops.py backend\risk_engine.py backend\weather.py ml\labels.py ml\predict.py ml\gradcam.py ml\train.py
```

## Demo Notes

- `agrisentinel.db`, `uploads/`, `.pytest_cache/`, `__pycache__/`, and `.keras`
  model files are local/generated artifacts and should not be committed.
- Simulated reports are disclosed demo data for dashboard proof, not field data.
- Grad-CAM appears only when TensorFlow and a trained `.keras` model are available.
- The fallback prediction path is deterministic and exists so the full app can be
  demoed before the Colab-trained model is copied locally.
