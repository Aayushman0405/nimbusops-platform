import os
import time
import logging
import mlflow
import mlflow.sklearn
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from starlette.responses import Response

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aurora-inference")

# ---------------- Env ----------------
API_KEY = os.getenv("API_KEY", "aurora-internal-key")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-server.aurora-system.svc.cluster.local:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "california-housing")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "stable")
CACHE_DIR = Path("/tmp/model-cache")

# Configure MLflow for RGW
os.environ['MLFLOW_S3_ENDPOINT_URL'] = os.getenv('MLFLOW_S3_ENDPOINT_URL', 'http://rook-ceph-rgw-mlflow-store.rook-ceph.svc.cluster.local:80')
os.environ['AWS_S3_FORCE_PATH_STYLE'] = 'true'
os.environ['MLFLOW_S3_IGNORE_TLS'] = 'true'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Set AWS credentials from secrets
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
if aws_access_key and aws_secret_key:
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
    logger.info("AWS credentials configured from environment")
else:
    logger.warning("AWS credentials not found in environment")

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# ---------------- App ----------------
app = FastAPI(title="Aurora Inference Runtime")

# ---------------- Metrics ----------------
REQUEST_COUNT = Counter(
    "aurora_inference_requests_total",
    "Total inference requests",
    ["status", "model_version"]
)

REQUEST_LATENCY = Histogram(
    "aurora_inference_request_latency_seconds",
    "Inference latency",
    ["model_version"]
)

MODEL_LOADED = Gauge(
    "aurora_inference_model_loaded",
    "Model loaded status (1=loaded, 0=not loaded)"
)

model = None
model_version = None
model_metadata = {}

# ---------------- Schemas ----------------
class PredictionRequest(BaseModel):
    inputs: list[list[float]]

# ---------------- Security ----------------
def verify_api_key(api_key: str = None):
    if API_KEY and api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

# ---------------- Model Loading ----------------
def load_model():
    global model, model_version, model_metadata

    try:
        logger.info(f"Loading model {MODEL_NAME} with alias '{MODEL_ALIAS}' from MLflow")
        logger.info(f"MLflow Tracking URI: {MLFLOW_TRACKING_URI}")

        # Create cache directory
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Get model version from alias
        client = mlflow.tracking.MlflowClient()
        
        # First, check if the model exists
        try:
            model_version_info = client.get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
            model_version = model_version_info.version
            run_id = model_version_info.run_id
            logger.info(f"Found model version: {model_version}, Run ID: {run_id}")
        except Exception as e:
            logger.error(f"Could not find model {MODEL_NAME} with alias {MODEL_ALIAS}: {e}")
            # Try to get latest version as fallback
            try:
                latest_versions = client.get_latest_versions(MODEL_NAME, stages=["None"])
                if latest_versions:
                    model_version = latest_versions[0].version
                    run_id = latest_versions[0].run_id
                    logger.info(f"Using latest version as fallback: {model_version}")
                else:
                    raise Exception("No versions found")
            except Exception as e2:
                logger.error(f"Could not find any versions: {e2}")
                MODEL_LOADED.set(0)
                return

        # Load model from MLflow
        model_uri = f"models:/{MODEL_NAME}/{model_version}"
        logger.info(f"Loading model from {model_uri}")
        model = mlflow.sklearn.load_model(model_uri)

        # Get metadata
        run = client.get_run(run_id)
        model_metadata = {
            "model_name": MODEL_NAME,
            "version": model_version,
            "alias": MODEL_ALIAS,
            "run_id": run_id,
            "metrics": run.data.metrics,
            "params": run.data.params,
            "timestamp": time.time()
        }

        MODEL_LOADED.set(1)
        logger.info(f"✅ Model loaded successfully: {MODEL_NAME} v{model_version} ({MODEL_ALIAS})")

    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        MODEL_LOADED.set(0)
        # Don't raise, just log - allow pod to start but show degraded status

# ---------------- Startup ----------------
@app.on_event("startup")
def startup_event():
    # Give MLflow time to initialize
    time.sleep(5)
    load_model()

# ---------------- Routes ----------------
@app.get("/health")
def health():
    return {
        "status": "healthy" if model else "degraded",
        "model_name": MODEL_NAME,
        "model_version": model_version,
        "model_alias": MODEL_ALIAS,
        "model_loaded": model is not None,
        "mlflow_uri": MLFLOW_TRACKING_URI,
        "s3_endpoint": os.environ.get('MLFLOW_S3_ENDPOINT_URL', 'not set')
    }

@app.post("/predict")
def predict(request: PredictionRequest, api_key: str = Depends(verify_api_key)):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    start_time = time.time()

    try:
        # Run inference
        predictions = model.predict(request.inputs).tolist()

        # Record latency
        latency = time.time() - start_time
        REQUEST_LATENCY.labels(model_version=model_version or "unknown").observe(latency)
        REQUEST_COUNT.labels(status="success", model_version=model_version or "unknown").inc()

        return {"predictions": predictions}

    except Exception as e:
        REQUEST_COUNT.labels(status="error", model_version=model_version or "unknown").inc()
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.post("/reload")
def reload_model(api_key: str = Depends(verify_api_key)):
    """Reload model (useful after new training)"""
    try:
        load_model()
        return {"status": "success", "message": f"Model reloaded: {MODEL_NAME} v{model_version} ({MODEL_ALIAS})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
