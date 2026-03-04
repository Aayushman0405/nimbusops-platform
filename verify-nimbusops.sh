#!/bin/bash

echo "🔍 Verifying NimbusOps deployment..."

# Check if controller is running
CONTROLLER_POD=$(kubectl get pods -n aurora-system -l app=nimbusops-controller -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$CONTROLLER_POD" ]; then
    echo "❌ NimbusOps controller not found!"
    exit 1
fi

echo "✅ Controller pod: $CONTROLLER_POD"

# Check logs
echo ""
echo "📋 Recent logs:"
kubectl logs -n aurora-system $CONTROLLER_POD --tail=10

# Check metrics endpoint
echo ""
echo "📊 Checking metrics endpoint..."
kubectl port-forward -n aurora-system $CONTROLLER_POD 8001:8001 &
PF_PID=$!
sleep 3

curl -s http://localhost:8001/metrics | grep nimbusops_ | head -10 || echo "❌ Metrics not available"

kill $PF_PID 2>/dev/null

# Check if it can see the target deployment
echo ""
echo "🎯 Target deployment status:"
kubectl get deployment -n aurora-system aurora-inference -o wide
