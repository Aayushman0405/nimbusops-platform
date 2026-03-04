import os
import mlflow
import mlflow.sklearn
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

# MLflow Configuration
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-server.aurora-system.svc.cluster.local:5000"))
mlflow.set_experiment("aurora-training")

# S3 Configuration for RGW
os.environ['MLFLOW_S3_ENDPOINT_URL'] = 'http://rook-ceph-rgw-mlflow-store.rook-ceph.svc.cluster.local:80'
os.environ['AWS_S3_FORCE_PATH_STYLE'] = 'true'
os.environ['MLFLOW_S3_IGNORE_TLS'] = 'true'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

MODEL_NAME = os.getenv("MODEL_NAME", "california-housing")

def main():
    print(f"🚀 Training {MODEL_NAME} with MLflow tracking...")
    print(f"MLflow Tracking URI: {mlflow.get_tracking_uri()}")
    
    # Get credentials from environment (just for logging)
    access_key = os.getenv('AWS_ACCESS_KEY_ID', 'not-set')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'not-set')[:5] + '...' if os.getenv('AWS_SECRET_ACCESS_KEY') else 'not-set'
    print(f"AWS Access Key: {access_key}")
    print(f"AWS Secret Key: {secret_key}")

    # Generate synthetic data
    print("📊 Generating synthetic dataset...")
    X = np.random.rand(1000, 8)
    y = np.random.rand(1000)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    with mlflow.start_run() as run:
        # Log parameters
        mlflow.log_param("model_type", "RandomForest")
        mlflow.log_param("n_estimators", 50)
        mlflow.log_param("random_state", 42)
        mlflow.log_param("features", X.shape[1])
        mlflow.log_param("samples", len(X))

        # Train model
        print("🔄 Training model...")
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate
        print("📈 Evaluating model...")
        y_pred = model.predict(X_test)
        score = r2_score(y_test, y_pred)

        # Log metrics
        mlflow.log_metric("r2_score", score)
        mlflow.log_metric("train_score", model.score(X_train, y_train))

        # Log model
        print("💾 Logging model to MLflow...")
        mlflow.sklearn.log_model(
            model,
            "model",
            registered_model_name=MODEL_NAME
        )

        # Get run info
        run_id = run.info.run_id
        artifact_uri = run.info.artifact_uri

        print(f"✅ Training complete!")
        print(f"📝 Run ID: {run_id}")
        print(f"📦 Artifact URI: {artifact_uri}")
        print(f"📊 R2 Score: {score:.4f}")

        # Set alias for latest model
        client = mlflow.tracking.MlflowClient()
        try:
            latest_version = client.get_latest_versions(MODEL_NAME, stages=["None"])[0].version
            client.set_registered_model_alias(MODEL_NAME, "latest", latest_version)
            print(f"🎯 Model registered with alias 'latest' (version {latest_version})")
        except Exception as e:
            print(f"⚠️ Could not set alias: {e}")

if __name__ == "__main__":
    main()
