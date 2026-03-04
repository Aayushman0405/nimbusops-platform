import time
import traceback
import json
from datetime import datetime
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import threading
import os

from prometheus_query import get_avg_cpu, get_memory_usage, get_request_rate
from decision import decide_replicas_enhanced
from deployment_scaler import scale_deployment

# Configuration - UPDATED for Aurora inference
NAMESPACE = os.getenv("TARGET_NAMESPACE", "aurora-system")
DEPLOYMENT = os.getenv("TARGET_DEPLOYMENT", "aurora-inference")
METRICS_PORT = int(os.getenv("METRICS_PORT", "8001"))

# Prometheus metrics
DECISIONS_TOTAL = Counter(
    'nimbusops_decisions_total',
    'Total number of scaling decisions',
    ['action']
)

REPLICAS_GAUGE = Gauge(
    'nimbusops_current_replicas',
    'Current number of replicas'
)

CPU_GAUGE = Gauge(
    'nimbusops_current_cpu',
    'Current CPU usage'
)

PREDICTED_CPU_GAUGE = Gauge(
    'nimbusops_predicted_cpu',
    'Predicted CPU usage'
)

COST_SAVINGS_GAUGE = Gauge(
    'nimbusops_cost_savings_usd_per_hour',
    'Estimated cost savings USD/hour'
)

REQUEST_RATE_GAUGE = Gauge(
    'nimbusops_request_rate',
    'Current request rate'
)

DECISION_LATENCY = Histogram(
    'nimbusops_decision_latency_seconds',
    'Decision latency in seconds'
)

class NimbusOpsController:
    def __init__(self):
        # Get current replicas from environment or default
        self.current_replicas = int(os.getenv("INITIAL_REPLICAS", "3"))
        self.decision_history = []
        self.running = True
        print(f"[NimbusOps] Initialized with target: {NAMESPACE}/{DEPLOYMENT}")

    def start_metrics_server(self):
        """Start Prometheus metrics server in background"""
        def run_server():
            start_http_server(METRICS_PORT)
            print(f"[NimbusOps] Metrics server started on port {METRICS_PORT}")

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

    def log_decision(self, decision: dict, action: str):
        """Log decision to history and metrics"""
        self.decision_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "action": action
        })

        # Keep only last 100 decisions
        if len(self.decision_history) > 100:
            self.decision_history = self.decision_history[-50:]

        # Update metrics
        DECISIONS_TOTAL.labels(action=action).inc()
        REPLICAS_GAUGE.set(self.current_replicas)
        CPU_GAUGE.set(decision.get("current_cpu", 0))
        PREDICTED_CPU_GAUGE.set(decision.get("predicted_load", 0))

        savings = decision.get("cost_impact", {}).get("cost_difference_usd_per_hour", 0)
        if savings > 0:
            COST_SAVINGS_GAUGE.set(savings)

        # Log to console
        print(f"[NimbusOps] Decision: {json.dumps(decision, indent=2, default=str)}")

    def run(self):
        print("[NimbusOps] Enhanced Controller starting...")
        print(f"[NimbusOps] Monitoring {DEPLOYMENT} in {NAMESPACE}")
        print(f"[NimbusOps] Metrics endpoint: :{METRICS_PORT}/metrics")

        # Start metrics server
        self.start_metrics_server()

        while self.running:
            try:
                with DECISION_LATENCY.time():
                    # Get current metrics
                    cpu = get_avg_cpu(NAMESPACE, DEPLOYMENT)
                    
                    # Also get request rate for better decisions
                    request_rate = get_request_rate(NAMESPACE, DEPLOYMENT)
                    REQUEST_RATE_GAUGE.set(request_rate)

                    # Make enhanced decision
                    decision = decide_replicas_enhanced(self.current_replicas, cpu)
                    desired = decision["replicas"]

                    # Take action if needed
                    if desired != self.current_replicas:
                        print(f"[NimbusOps] Scaling {self.current_replicas} → {desired}")
                        print(f"[NimbusOps] Reason: {decision['decision_reason']}")

                        try:
                            scale_deployment(NAMESPACE, DEPLOYMENT, desired)
                            self.current_replicas = desired
                            self.log_decision(decision, "scaled")
                        except Exception as scale_error:
                            print(f"[NimbusOps] Scale failed: {scale_error}")
                            self.log_decision(decision, "failed")
                    else:
                        print(f"[NimbusOps] No change (cpu={cpu:.3f}, predicted={decision['predicted_load']:.3f}, req_rate={request_rate:.2f})")
                        self.log_decision(decision, "no_change")

            except Exception as e:
                print(f"[NimbusOps] ERROR in main loop: {e}")
                traceback.print_exc()

            time.sleep(60)  # Check every minute

    def stop(self):
        self.running = False

if __name__ == "__main__":
    controller = NimbusOpsController()

    try:
        controller.run()
    except KeyboardInterrupt:
        print("\n[NimbusOps] Shutting down...")
        controller.stop()
