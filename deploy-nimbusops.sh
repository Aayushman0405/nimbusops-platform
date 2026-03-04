#!/bin/bash

set -e

echo "🚀 Deploying NimbusOps Controller to monitor Aurora Inference"

# Navigate to scaler directory
cd ~/nimbusops-platform/control-plane/scaler

# Fix Dockerfile (ensure it's correct)
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files from current directory
COPY *.py ./

# Expose metrics port
EXPOSE 8001

# Run the main application
CMD ["python", "-u", "main.py"]
EOF

# Build the Docker image
echo "🏗️ Building NimbusOps controller image..."
docker build -t aayud/nimbusops-controller:latest .

# Push to Docker Hub (optional, can use local image)
echo "📤 Pushing image to Docker Hub..."
docker push aayud/nimbusops-controller:latest || echo "⚠️ Push failed, using local image"

# Go back to home directory
cd ~

# Ensure Aurora inference is running
echo "📊 Ensuring Aurora inference is running..."
kubectl scale deployment -n aurora-system aurora-inference --replicas=3 2>/dev/null || echo "aurora-inference not found, will continue"
kubectl scale deployment -n aurora-system aurora-inference-canary --replicas=1 2>/dev/null || echo "aurora-inference-canary not found, will continue"

# Apply RBAC
echo "🔐 Applying RBAC..."
kubectl apply -f ~/nimbusops-platform/k8s/base/rbac/nimbusops-rbac.yaml

# Create/update deployment with correct image
echo "📦 Creating/updating deployment..."

# First, delete existing deployment if it exists (to avoid image pull issues)
kubectl delete deployment nimbusops-controller -n aurora-system 2>/dev/null || true

# Apply fresh deployment
cat << 'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nimbusops-controller
  namespace: aurora-system
  labels:
    app: nimbusops-controller
    version: v1.0-enhanced
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nimbusops-controller
  template:
    metadata:
      labels:
        app: nimbusops-controller
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8001"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: aurora-sa
      containers:
        - name: controller
          image: aayud/nimbusops-controller:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 8001
              name: metrics
          env:
            - name: PROMETHEUS_URL
              value: http://prometheus.monitoring.svc.cluster.local:9090
            - name: TARGET_NAMESPACE
              value: "aurora-system"
            - name: TARGET_DEPLOYMENT
              value: "aurora-inference"
            - name: INITIAL_REPLICAS
              value: "3"
            - name: METRICS_PORT
              value: "8001"
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
          livenessProbe:
            httpGet:
              path: /metrics
              port: 8001
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /metrics
              port: 8001
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: nimbusops-controller-metrics
  namespace: aurora-system
  labels:
    app: nimbusops-controller
spec:
  selector:
    app: nimbusops-controller
  ports:
    - port: 8001
      targetPort: 8001
      name: metrics
EOF

# Wait for deployment
echo "⏳ Waiting for controller to be ready..."
sleep 10
kubectl rollout status deployment/nimbusops-controller -n aurora-system --timeout=120s || true

# Show status
echo "✅ Deployment complete!"
echo ""
echo "📊 Controller status:"
kubectl get pods -n aurora-system -l app=nimbusops-controller
echo ""
echo "📈 Metrics endpoint:"
kubectl get svc -n aurora-system nimbusops-controller-metrics
echo ""
echo "📋 Controller logs:"
kubectl logs -n aurora-system deployment/nimbusops-controller --tail=50
