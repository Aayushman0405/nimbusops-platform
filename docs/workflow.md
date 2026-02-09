# End-to-End Workflow 🔄

This document explains how NimbusOps behaves from **commit → model → traffic → scaling**.

---

## 1️⃣ Code Push

Developer pushes code to `main`.

GitHub Actions:
- Runs unit tests
- Builds Docker images
- Pushes to Docker Hub
- Deploys to Kubernetes

---

## 2️⃣ Model Training

apiVersion: aurora.io/v1alpha1
kind: MLTrainingJob
Flow:
CR applied
Aurora Operator detects event
Kubernetes Job created
Model trained
Artifact stored in CephFS
Metadata generated


3️⃣ Model Deployment (Canary)
kind: MLDeployment
strategy:
  type: Canary

Canary pods deployed
Traffic split via NGINX
Metrics collected
SLOs evaluated

4️⃣ Inference Runtime
Fetches model via Control Plane
Caches artifacts locally
Serves predictions
Emits latency & error metrics

5️⃣ Autoscaling (NimbusOps)
Every minute:
Fetch CPU metrics from Prometheus
Predict future load
Evaluate scaling thresholds
Compute cost impact
Apply policy constraints
Scale deployment (or not)
Emit decision metrics

6️⃣ Observability & Feedback
Grafana dashboards show:
Predicted vs actual CPU
Replica changes
Cost savings
Decision breakdown
Latency histograms

7️⃣ Rollback (If Needed)
Manual GitHub Action:
View rollout history
Rollback to previous revision
Verify deployment health


Result
A self-correcting, explainable, cost-aware ML platform.

