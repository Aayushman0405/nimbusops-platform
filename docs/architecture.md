```md
# Architecture Overview 🏗️

NimbusOps follows a **multi-control-plane architecture** with clear separation of concerns.

---

## High-Level Architecture

            ┌────────────┐
            │   Users    │
            └─────┬──────┘
                  │
          ┌───────▼────────┐
          │   NGINX Ingress│
          └───────┬────────┘
                  │
    ┌─────────────▼──────────────┐
    │     Aurora Control Plane   │
    │  (FastAPI + Security + API)│
    └─────────────┬──────────────┘
                  │
 ┌────────────────▼─────────────────┐
 │      Shared Model Registry       │
 │        (CephFS RWX PVC)          │
 └────────────────┬─────────────────┘
                  │
┌─────────────────▼────────────────────┐
│         Inference Deployments        │
│         Stable Pods Canary Pods      │
└──────────────────┬───────────────────┘
                   │
           ┌───────▼─────────┐
           │    Prometheus   │
           │     Grafana     │
           └───────┬─────────┘
                   │
         ┌─────────▼───────────┐
         │ NimbusOps Controller│
         │ (Intelligent Scaling│
         │ + Cost Decisions)   │
         └─────────────────────┘


---

## Control Planes

### 1️⃣ NimbusOps Controller
Responsible for **autoscaling decisions**.

- Reads live metrics from Prometheus
- Predicts future CPU load
- Calculates cost impact
- Enforces policy constraints
- Scales Kubernetes deployments
- Emits decision telemetry

---

### 2️⃣ Aurora Control Plane
Responsible for **ML lifecycle APIs**.

- Model registry
- Artifact serving
- Cluster inspection
- Storage introspection
- Secured internal APIs

---

### 3️⃣ Aurora Operator
Kubernetes-native automation using **CRDs**:

- `MLTrainingJob`
- `MLDeployment`

Handles:
- Training job creation
- Versioned model storage
- Canary deployment status
- CR lifecycle management

---

## Observability Layer

- **Prometheus**
  - Metrics scraping
  - Decision telemetry
- **Grafana**
  - Cost savings
  - Prediction accuracy
  - Replica behavior
  - Decision latency
- **Node Exporter + KSM**
  - Cluster health
  - Resource visibility

---

## Storage Architecture

| Layer                | Purpose                 |
|----------------------|-------------------------|
|CephFS RWX PVC        | Shared model registry   |  
|Versioned directories | Immutable model versions| 
|Aliases               | Stable / Canary routing | 


## Security Model

- Internal API keys
- ServiceAccount-based RBAC
- Namespace isolation
- No public cluster-admin permissions

---

## Design Philosophy

> **Infrastructure should explain itself.**

Every NimbusOps decision is:
- Measured
- Logged
- Visualized
- Justified
