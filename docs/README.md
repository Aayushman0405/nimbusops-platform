# NimbusOps Platform 🚀
**Cost-Aware Intelligent Autoscaling + ML Platform (Aurora)**

NimbusOps is a cloud-native, production-style platform that combines:

- Intelligent, cost-aware autoscaling (beyond HPA)
- Full ML lifecycle management (training → registry → deployment)
- Canary deployments with SLO-based decisioning
- GitOps-driven Kubernetes operations
- Deep observability (Prometheus + Grafana)

This project is designed to **mirror real-world systems** used at scale by companies like Uber, Netflix, and Stripe — but built end-to-end from scratch.

---

## Key Highlights

- 🧠 **Custom Autoscaler** (NimbusOps Controller)
- 💰 **Cost-Aware Scaling Decisions**
- 📈 **Predictive Scaling (CPU trend forecasting)**
- 🔁 **Canary ML Deployments**
- 🧪 **Custom Kubernetes Operators (CRDs + Kopf)**
- 📊 **First-class Observability**
- 🔐 **Secure Internal APIs**
- ⚙️ **GitHub Actions CI/CD + Rollbacks**

---

## Core Components

| Component | Description |
|---------|------------|
NimbusOps Controller | Intelligent autoscaling engine
Aurora Control Plane | ML model registry & cluster API
Aurora Operator | Kubernetes-native ML automation
Inference Runtime | Online model serving
Observability Stack | Prometheus, Grafana, Alerts
Storage Layer | RWX CephFS model registry

---

## Why NimbusOps?

Traditional autoscaling reacts **after** things break.

NimbusOps:
- Predicts load
- Weighs **performance vs cost**
- Makes explainable decisions
- Emits metrics for every choice

> This is **decision-driven infrastructure**, not reactive automation.

---

## Repository Structure

```text
control-plane/
k8s/
docs/
.github/
