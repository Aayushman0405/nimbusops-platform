import time
from typing import Dict, Any
import json

class CostAwareDecisionEngine:
    def __init__(self):
        # Policy configuration
        self.policies = {
            "default": {
                "max_replicas": 10,
                "min_replicas": 1,
                "target_cpu": 0.65,  # Adjusted for cost efficiency
                "scale_up_threshold": 0.75,
                "scale_down_threshold": 0.35,
                "cost_weight": 0.4,  # How much cost influences decision (0-1)
                "performance_weight": 0.6,
                "min_savings_percent": 15,  # Minimum % savings to trigger scale-down
                "prediction_window_minutes": 30
            }
        }
        
        # GCP/AWS cost profiles (simplified - will be enhanced)
        self.cost_profiles = {
            "gcp_e2_medium": {
                "cost_per_hour": 0.0335,  # USD
                "cost_per_replica_per_hour": 0.01675,  # Assuming 2 cores per pod
                "region": "asia-south1"
            },
            "aws_t3_medium": {
                "cost_per_hour": 0.0416,
                "cost_per_replica_per_hour": 0.0208,
                "region": "ap-south-1"
            }
        }
        
        # Historical data for prediction (in-memory cache)
        self.history = {
            "cpu": [],
            "timestamps": [],
            "replicas": []
        }
        
    def predict_future_load(self, current_cpu: float, history_length: int = 10) -> float:
        """Simple linear prediction based on recent trend"""
        if len(self.history["cpu"]) < 3:
            return current_cpu
            
        # Simple moving average with trend
        recent = self.history["cpu"][-min(5, len(self.history["cpu"])):]
        avg = sum(recent) / len(recent)
        
        # Detect trend
        if len(recent) >= 3:
            trend = (recent[-1] - recent[0]) / len(recent)
            predicted = current_cpu + (trend * 6)  # Project 6 intervals ahead
        else:
            predicted = avg
            
        return max(0.1, min(0.95, predicted))  # Bound prediction
    
    def calculate_cost_impact(self, current_replicas: int, proposed_replicas: int) -> Dict[str, float]:
        """Calculate cost difference between current and proposed state"""
        profile = self.cost_profiles["gcp_e2_medium"]
        
        current_cost = current_replicas * profile["cost_per_replica_per_hour"]
        proposed_cost = proposed_replicas * profile["cost_per_replica_per_hour"]
        cost_difference = current_cost - proposed_cost
        percent_savings = (cost_difference / current_cost * 100) if current_cost > 0 else 0
        
        return {
            "current_cost_usd_per_hour": round(current_cost, 4),
            "proposed_cost_usd_per_hour": round(proposed_cost, 4),
            "cost_difference_usd_per_hour": round(cost_difference, 4),
            "percent_savings": round(percent_savings, 2)
        }
    
    def check_policy_constraints(self, current: int, proposed: int, policy_name: str = "default") -> bool:
        """Ensure proposed replicas meet policy constraints"""
        policy = self.policies[policy_name]
        
        if proposed < policy["min_replicas"]:
            return False
        if proposed > policy["max_replicas"]:
            return False
            
        # Ensure we don't scale down too aggressively during predicted peak
        if proposed < current:
            # Check if we're approaching predicted peak time
            current_hour = time.localtime().tm_hour
            if 9 <= current_hour <= 17:  # Business hours
                # Be conservative about scaling down during work hours
                if (current - proposed) > 1:
                    return False
                    
        return True
    
    def decide_replicas(self, current: int, cpu: float, 
                       additional_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enhanced decision with cost awareness and prediction
        
        Returns: {
            "replicas": int,
            "decision_reason": str,
            "cost_impact": Dict,
            "predicted_load": float,
            "policy_used": str
        }
        """
        # Update history
        self.history["cpu"].append(cpu)
        self.history["timestamps"].append(time.time())
        self.history["replicas"].append(current)
        
        # Keep history manageable
        if len(self.history["cpu"]) > 100:
            self.history["cpu"] = self.history["cpu"][-50:]
            self.history["timestamps"] = self.history["timestamps"][-50:]
            self.history["replicas"] = self.history["replicas"][-50:]
        
        policy = self.policies["default"]
        predicted_cpu = self.predict_future_load(cpu)
        
        # Base decision on predicted load
        base_decision = current
        
        if predicted_cpu > policy["scale_up_threshold"]:
            base_decision = min(current + 1, policy["max_replicas"])
            reason = f"Predicted CPU ({predicted_cpu:.2f}) > threshold ({policy['scale_up_threshold']})"
        elif predicted_cpu < policy["scale_down_threshold"]:
            base_decision = max(current - 1, policy["min_replicas"])
            reason = f"Predicted CPU ({predicted_cpu:.2f}) < threshold ({policy['scale_down_threshold']})"
        else:
            base_decision = current
            reason = f"Predicted CPU ({predicted_cpu:.2f}) within stable range"
        
        # Apply cost optimization
        cost_impact = self.calculate_cost_impact(current, base_decision)
        
        # If scaling down, check if it meets minimum savings policy
        if base_decision < current:
            if cost_impact["percent_savings"] < policy["min_savings_percent"]:
                # Not enough savings, don't scale down
                base_decision = current
                reason = f"Scale-down blocked: Savings ({cost_impact['percent_savings']}%) < minimum ({policy['min_savings_percent']}%)"
        
        # Final policy check
        if not self.check_policy_constraints(current, base_decision):
            base_decision = current
            reason = "Blocked by policy constraints"
        
        return {
            "replicas": base_decision,
            "decision_reason": reason,
            "cost_impact": cost_impact,
            "predicted_load": predicted_cpu,
            "policy_used": "default",
            "current_cpu": cpu,
            "timestamp": time.time()
        }

# Singleton instance
decision_engine = CostAwareDecisionEngine()

def decide_replicas(current: int, cpu: float) -> int:
    """Backward compatibility wrapper"""
    decision = decision_engine.decide_replicas(current, cpu)
    return decision["replicas"]

def decide_replicas_enhanced(current: int, cpu: float) -> Dict[str, Any]:
    """Enhanced decision with full details"""
    return decision_engine.decide_replicas(current, cpu)
