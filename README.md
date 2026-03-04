NimbusOps Platform
Intelligent Kubernetes Autoscaling with Cost-Aware Decision Engine


NimbusOps is an intelligent, cost-aware autoscaling platform for Kubernetes that optimizes ML workload deployments. It combines real-time metrics, predictive analytics, and cost optimization to make smart scaling decisions.

🎯 Key Features
Cost-Aware Autoscaling: Makes scaling decisions based on both performance metrics and cost implications
Predictive Scaling: Uses historical data to predict future load and scale proactively
Multi-Cloud Cost Models: Built-in cost profiles for GCP and AWS
Real-time Metrics: Prometheus integration for live monitoring
Business Hours Awareness: Intelligent scaling that respects business hours vs. off-hours
Grafana Dashboards: Comprehensive visualization of scaling decisions and cost savings
Canary Support: Seamless integration with canary deployments
MLflow Integration: Works with MLflow model registry for ML workloads

🏗️ Architecture

┌─────────────────────────────────────────────────────────────┐
│                      NimbusOps Platform                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │   Decision      │    │   Prometheus    │                 │
│  │    Engine       │◄───│    Queries      │                 │
│  └────────┬────────┘    └─────────────────┘                 │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │     Scaler      │───▶│   Kubernetes    │                │
│  │   Controller    │    │     API         │                 │
│  └─────────────────┘    └─────────────────┘                 │
│                                                             |
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │    Metrics      │    │    Grafana      │                 │
│  │    Exporter     │───▶│   Dashboard     │                 │
│  └─────────────────┘    └─────────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Target Workload                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │   Inference     │    │    Canary       │                 │
│  │   (Stable)      │    │   (Testing)     │                 │
│  └─────────────────┘    └─────────────────┘                 │
│                                                             │
│  ┌─────────────────┐                                        │
│  │    MLflow       │                                        │
│  │    Registry     │                                        │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘


Components
Decision Engine (decision.py)
Cost-aware scaling logic
Predictive load analysis
Policy enforcement
Business hours awareness
Prometheus Query Layer (prometheus_query.py)

Real-time metric collection
CPU/Memory usage tracking
Request rate monitoring
Latency measurements

Scaler Controller (main.py)
Main control loop
Metric aggregation
Decision execution
Prometheus metrics export

Kubernetes Integration (deployment_scaler.py)
Direct K8s API interaction
Deployment scaling
RBAC integration



💻 Tech Stack

Component	    Technology	    Purpose
Language	    Python 3.11+	  Core logic
ML Framework	scikit-learn	  Prediction models
Monitoring	  Prometheus	    Metrics collection
Visualization	Grafana	        Dashboards
Container	    Docker	        Packaging
Orchestration	Kubernetes	    Deployment
ML Registry	  MLflow	        Model management
API	          FastAPI	        Inference endpoints
CI/CD	        GitHub Actions	Automation


📊 Testing the Inference API
The platform includes a sample ML inference service for testing. Here's how to use it:

1. Access the FastAPI Documentation
Once deployed, the inference service exposes interactive API docs:

http://inference.aurora.yourdomain.com/docs
Or via port-forward:


kubectl port-forward -n aurora-system service/aurora-inference 8080:80
Then visit: http://localhost:8080/docs

2. API Endpoints
Health Check

curl -X GET http://localhost:8080/health
Response:

json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "california-housing",
  "model_version": "v1.0.0"
}
Prediction (with API Key)
bash
curl -X POST http://localhost:8080/predict \
  -H "x-api-key: aurora-internal-key" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
      [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    ]
  }'

Response:

{
  "predictions": [4.52, 5.78]
}

Metrics

curl http://localhost:8080/metrics

Returns Prometheus-formatted metrics including:
Request counts
Latency histograms
Model load status

3. FastAPI Interactive Testing
Visit http://localhost:8080/docs to use the Swagger UI:
Authorize: Click "Authorize" and enter your API key
Try endpoints: Expand any endpoint, click "Try it out"
Execute: Fill parameters and execute requests

4. Sample Test Script
python
import requests
import json

# Configuration
BASE_URL = "http://localhost:8080"
API_KEY = "aurora-internal-key"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

# Test health
health = requests.get(f"{BASE_URL}/health")
print(f"Health: {health.json()}")

# Test prediction
test_data = {
    "inputs": [[1.5, 2.3, 3.7, 4.1, 5.2, 6.8, 7.4, 8.9]]
}
response = requests.post(
    f"{BASE_URL}/predict",
    headers=HEADERS,
    data=json.dumps(test_data)
)
print(f"Prediction: {response.json()}")


🧠 Decision Logic
Scaling Algorithm
The decision engine uses a weighted scoring system:

text
Score = (Performance_Weight × CPU_Utilization) + 
        (Cost_Weight × Cost_Efficiency)
Thresholds
Threshold	Value	Action
Scale Up	> 0.75 CPU	+1 replica
Scale Down	< 0.35 CPU	-1 replica
Min Savings	15%	Minimum savings to scale down
Business Hours Awareness
Business Hours (9 AM - 5 PM): Conservative scaling
Off-Hours: Aggressive cost optimization
Weekends: Maximum cost savings

Prediction Model
Uses moving average with trend detection:
Historical window: Last 5 data points
Prediction horizon: 6 intervals ahead
Bounded between 0.1 and 0.95 CPU


🔧 Configuration
Environment Variables
Variable	Default	Description
TARGET_NAMESPACE	aurora-system	Namespace to monitor
TARGET_DEPLOYMENT	aurora-inference	Deployment to scale
PROMETHEUS_URL	http://prometheus.monitoring.svc:9090	Prometheus server
INITIAL_REPLICAS	3	Starting replica count
METRICS_PORT	8001	Metrics export port
Policy Configuration
Edit decision.py to adjust:

self.policies = {
    "default": {
        "max_replicas": 10,
        "min_replicas": 1,
        "target_cpu": 0.65,
        "scale_up_threshold": 0.75,
        "scale_down_threshold": 0.35,
        "cost_weight": 0.4,
        "performance_weight": 0.6,
        "min_savings_percent": 15,
        "prediction_window_minutes": 30
    }
}


Cost Profiles
Configure cloud provider costs:

self.cost_profiles = {
    "gcp_e2_medium": {
        "cost_per_hour": 0.0335,
        "cost_per_replica_per_hour": 0.01675,
        "region": "asia-south1"
    },
    "aws_t3_medium": {
        "cost_per_hour": 0.0416,
        "cost_per_replica_per_hour": 0.0208,
        "region": "ap-south-1"
    }
}


🔒 Security
Best Practices
API Keys - Always use headers, never URLs
RBAC - Least privilege principle
Network Policies - Restrict pod communication

