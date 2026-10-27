# Pumpkin Seed API

**Classify pumpkin seed varieties from shape measurements, and see which measurements drove each decision.**

![CI](https://github.com/Sujan-13/pumpkin-seed-api/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-model-orange)
![SHAP](https://img.shields.io/badge/SHAP-explainability-blueviolet)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7)

### 🔗 [Live demo (interactive API docs)](https://pumpkin-seed-api.onrender.com/docs)

> The demo runs on a free tier, so the first request after inactivity can take about a minute while the service wakes up.

![Swagger UI of the live API](docs/swagger-ui.png)

---

## Why this project exists

A trained model is only useful when other software can call it. This project takes a seed-classification model from a notebook to a service that is validated, explained, tested, containerized, and deployed:

1. **Model:** an XGBoost classifier on 12 shape features, compared against logistic regression.
2. **Explainability:** every prediction can be explained with SHAP.
3. **API:** a validated REST service built with FastAPI and Pydantic.
4. **Packaging:** a multi-stage Docker build with a non-root user and a health check.
5. **Quality:** automated tests with pytest, run by GitHub Actions on every push.
6. **Deployment:** live on Render, redeployed from `main`.

---

## API

| Endpoint | Method | Description |
|---|---|---|
| `/predict` | POST | Predicted seed variety and its probability |
| `/explain` | POST | The measurements that pushed this prediction toward or away from each variety (SHAP values) |
| `/health` | GET | Health check used by Docker and Render |

Inputs are validated with Pydantic. Every field has a range taken from the training data, so a negative area or a missing field returns a `422` error with a clear message and never reaches the model.

### Try it

```bash
curl -X POST https://pumpkin-seed-api.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Area": 56276, "Perimeter": 888.242, "Major_Axis_Length": 326.1485,
    "Minor_Axis_Length": 220.2388, "Convex_Area": 56831, "Equiv_Diameter": 267.6805,
    "Eccentricity": 0.7376, "Solidity": 0.9902, "Extent": 0.7453,
    "Roundness": 0.8963, "Aspect_Ration": 1.4809, "Compactness": 0.8207
  }'
```

Response:

```json
{
  "seed_type": "Ürgüp Sivrisi",
  "probability": 0.9756
}
```

`POST /explain` with the same body returns the measurements that mattered most for this seed. A positive SHAP value pushes the prediction toward the positive class, and a negative value pushes it away.

---

## Where the measurements come from

The API takes **numbers, not images**. In the original dataset, seeds were photographed and each seed was separated from the background. Its outline was then measured, and each seed became one row of 12 values:

| Group | Measurements |
|---|---|
| Size | `Area`, `Perimeter`, `Convex_Area`, `Equiv_Diameter` |
| Fitted ellipse | `Major_Axis_Length`, `Minor_Axis_Length`, `Eccentricity`, `Aspect_Ration` |
| Shape ratios | `Solidity`, `Extent`, `Roundness`, `Compactness` |

Lengths and areas are in pixels. That means inputs must come from the same kind of image setup as the training data, or the pixel values will not match what the model learned.

---

## Architecture

```mermaid
flowchart LR
    Client["Client or Swagger UI"] -->|"JSON over HTTPS"| API["FastAPI app in a Docker container"]
    API --> Val["Pydantic input validation"]
    Val --> Model["XGBoost model"]
    Model --> API
    API -->|"POST /explain"| Shap["SHAP TreeExplainer"]
    API -->|"log predictions"| DB[("PostgreSQL on Render")]
```

**Tech stack:** Python · FastAPI · Pydantic · scikit-learn · XGBoost · SHAP · SQLModel / SQLAlchemy · PostgreSQL · Docker · pytest · GitHub Actions · Render

---

## The model

- **Data:** the Pumpkin Seeds dataset, 2,500 seeds of two varieties, 12 numeric features. https://www.kaggle.com/datasets/muratkokludataset/pumpkin-seeds-dataset
- **Models compared:** logistic regression and XGBoost.

### Results

| Metric                 | Value |
|------------------------|-------|
| Cross-validation score | 0.89  |
| Test accuracy          | 0.87  |
| F1 Score               | 0.87  |

### What the model relies on

![SHAP summary plot](docs/swagger-ui.png)

The most influential features are `Compactness`, `Eccentricity`, `Solidity`, `Major_Axis_Length`, and `Minor_Axis_Length`. Almost all of them describe **how elongated or round a seed is**. Low compactness, low roundness, high eccentricity, a long major axis, and a short minor axis all push the prediction the same way. The model is separating long, narrow seeds from short, round ones, which agrees with the geometry and is a good sign that it learned real shape differences.

### Limitations

- Many features are built from the same measurements (for example compactness uses the equivalent diameter and the major axis), so they are strongly correlated. SHAP shares credit among correlated features, so `Area` and `Convex_Area` showing almost no effect does not mean size is unimportant. Read the result as a group ("elongation features dominate"), not as a ranking of single features.
- `Solidity` ranks high even though its range is narrow. It may reflect real outline differences, or how the images were segmented.
- Inputs are pixel measurements, so they only make sense for images prepared like the training data.
- SHAP shows what the model uses. It does not show what causes the difference between varieties.

---

## Engineering

### Docker (multi-stage build)

```dockerfile
# Stage 1: build the Python environment
FROM python:3.12-slim AS builder
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
# Install XGBoost without its optional GPU dependencies to keep the image small
RUN <install every requirement except xgboost> \
    && pip install --no-deps xgboost==2.1.3

# Stage 2: small runtime image
FROM python:3.12-slim AS runtime
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY model ./model
RUN groupadd --system app && useradd --system --gid app --create-home app \
    && chown -R app:app /app
USER app
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

*(Simplified. The full file is in the repository.)*

| Choice | Why |
|---|---|
| Multi-stage build | Build leftovers stay in the first stage, so the final image is smaller and exposes less |
| XGBoost installed with `--no-deps` | Skips its optional GPU libraries, which this CPU-only API never uses, and keeps the image small |
| Pinned versions | The model is loaded with the same library versions it was saved with |
| Dependencies copied before the code | Docker caches the slow install layer, so code changes rebuild quickly |
| Only `app/` and `model/` are copied | Keeps notebooks and data out of the image |
| Non-root user | A compromised process has far fewer permissions |
| `HEALTHCHECK` on `/health` | Docker can detect an unhealthy container |
`compose.yaml` runs the container for local use with a persistent volume for the local database.

### Database

Predictions are logged with SQLModel on top of SQLAlchemy. The connection string comes from the `DATABASE_URL` environment variable:

- **Production:** PostgreSQL on Render. This service writes to its own table (`PredictionSeedLog`) in a PostgreSQL instance shared with another project, and the URL is stored as an environment variable on the host and is never committed.
- **Local and tests:** without `DATABASE_URL`, the app falls back to a local SQLite file, so it runs with no database server.

Tables are created on startup in FastAPI's `lifespan` handler.

### Testing

```bash
python -m pytest -q
```

The tests cover:

- the health endpoint
- a valid prediction returns `200`
- invalid input (such as a negative area) is rejected with `422`
- the explain endpoint returns the contributing features

`pytest.ini` sets `pythonpath = .` and `testpaths = tests`, so tests run the same way locally and in CI.

### Continuous integration (GitHub Actions)

```mermaid
flowchart LR
    A["git push or pull request"] --> B["GitHub Actions runner"]
    B --> C["Install dependencies"]
    C --> D["Run pytest"]
    D --> E["Validate compose file"]
    E --> F["Build Docker image"]
    F --> G{"All steps pass?"}
    G -->|"yes"| H["Safe to merge, Render redeploys"]
    G -->|"no"| I["Fix before merging"]
```

On every push and pull request, the workflow installs the dependencies on a clean machine, runs the tests, validates `compose.yaml`, and builds the Docker image. The cheap checks run first so a failure shows up quickly. A clean machine matters: an early run caught packages that were installed on my laptop but missing from `requirements.txt`, which is exactly the kind of "works on my machine" bug CI exists to find.

![GitHub Actions passing](docs/ci-passing.png)

### Deployment

The service runs on [Render](https://render.com) as a Docker web service built from this repository. Pushing to `main` triggers a new build and deploy, and Render uses `/health` to decide when the new version is ready.

---

## Run it yourself

### With Docker

```bash
git clone https://github.com/Sujan-13/pumpkin-seed-api.git
cd pumpkin-seed-api
docker compose up --build
```

Open http://localhost:8000/docs.

### Without Docker

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (use source .venv/bin/activate on Linux or macOS)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Use PostgreSQL locally

Create a `.env` file (it is in `.gitignore`) with one line and no quotes:

```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

### Configuration

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Database connection string | local SQLite file |

---

## Project structure

```
app/                 FastAPI application (main.py, schemas.py, db.py)
model/               Saved model pipeline
tests/               API tests
Dataset/             Source data
train.ipynb          Model development, comparison, and SHAP analysis
Dockerfile           Multi-stage container build
compose.yaml         Local run with a persistent volume
pytest.ini           Test configuration
requirements.txt     Python dependencies
.github/workflows/   CI pipeline
```

## Skills demonstrated

| Skill | Where to see it |
|---|---|
| Python backend and REST API design | `app/main.py`, `app/schemas.py` |
| Input validation | Pydantic models, `422` responses |
| ML modelling and comparison | notebook (XGBoost, logistic regression) |
| Explainable AI | SHAP plot and the `/explain` endpoint |
| Databases and ORM | `app/db.py` (SQLModel, PostgreSQL) |
| Docker | multi-stage `Dockerfile`, `compose.yaml` |
| Automated testing | `tests/`, `pytest.ini` |
| CI/CD | `.github/workflows` |
| Cloud deployment | Render web service |

## Possible improvements

- Add an image-upload endpoint that extracts the measurements from a photo
- Compare against a small CNN trained directly on the images
- Remove redundant features and check whether the score changes
- Add authentication and rate limiting
---

## Author

**Sujan Gupta** · Electronics and Communication Engineering graduate (2026), Thapathali Engineering Campus

[GitHub](https://github.com/Sujan-13) · [LinkedIn](https://www.linkedin.com/in/sujan-g-545aa7187)