import pandas as pd
from fastapi import FastAPI, Query
from contextlib import asynccontextmanager
from sqlmodel import select
from app.db import create_db_and_tables, PredictionPublic, SessionDep, PredictionSeedLog, PredictionBase
from app.schemas import SeedIn
import joblib
from pathlib import Path
import shap
from typing import Annotated

MODEL_PATH = Path(__file__).resolve().parent.parent / 'model' / 'pipeline.joblib'
model = joblib.load(MODEL_PATH)
prep = model[:-1]

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title='Pumpkin Seed API', lifespan=lifespan)

@app.get('/health')
def health():
    return {
    'status':'ok'
    }

@app.post('/predict')
def get_prediction(s:SeedIn, session: SessionDep):
    seed = pd.DataFrame([s.model_dump()])
    prediction = model.predict_proba(prep.transform(seed))[0]
    if prediction[0] > 0.5:
        response = {
            'seed_type':'Çerçevelik',
            'probability':round(float(prediction[0]),4)
        }
        log = PredictionSeedLog(
            seed_data=s.model_dump(),
            prediction='Çerçevelik',
            probability=prediction[0]
        )
    else:
        response = {
            'seed_type': 'Ürgüp Sivrisi',
            'probability': round(float(prediction[1]),4)
        }
        log = PredictionSeedLog(
            seed_data=s.model_dump(),
            prediction='Ürgüp Sivrisi',
            probability=prediction[1]
        )
    session.add(log)
    session.commit()
    session.refresh(log)
    return response

@app.post('/explain')
def get_shap_explanation(s:SeedIn):
    s = pd.DataFrame([s.model_dump()])
    explainer = shap.TreeExplainer(model.named_steps['model'])
    transformed_X = prep.transform(s)
    shap_values = explainer.shap_values(transformed_X)[0]
    feat = prep.get_feature_names_out()
    combined = sorted(zip(feat, shap_values), key=lambda x: abs(x[1]), reverse=True)[:5]
    prediction = 'Çerçevelik' if (model.predict_proba(prep.transform(s))[0,0]>0.5) else 'Ürgüp Sivrisi'
    response = {
        'seed_type':prediction,
        'impactful features':[
            {
              'feature':feat,
              'impact':round(float(impact),4)
            }
            for feat,impact in combined
        ]
    }
    return response


@app.get("/predictions/", response_model=list[PredictionPublic])
def read_prediction_logs(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    predictions = session.exec(select(PredictionSeedLog).offset(offset).limit(limit)).all()
    return predictions

