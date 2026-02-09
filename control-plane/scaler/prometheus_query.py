import requests
import os
from typing import List, Dict, Any

PROM_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus.monitoring.svc.cluster.local:9090"
)

def query(promql: str) -> List[Dict[str, Any]]:
    """Execute PromQL query and return results"""
    try:
        resp = requests.get(
            f"{PROM_URL}/api/v1/query",
            params={"query": promql},
            timeout=10
        )
        resp.raise_for_status()
        
        result = resp.json()["data"]["result"]
        return result
    except Exception as e:
        print(f"[Prometheus] Query failed: {e}")
        return []

def get_avg_cpu(namespace: str, deployment: str) -> float:
    """Get average CPU usage for deployment"""
    promql = f'''
    avg(
      rate(container_cpu_usage_seconds_total{{
        namespace="{namespace}",
        pod=~"{deployment}.*",
        container!="POD"
      }}[2m])
    ) by (pod)
    '''
    
    results = query(promql)
    if not results:
        return 0.0
    
    # Calculate average across all pods
    cpu_values = []
    for result in results:
        try:
            cpu_values.append(float(result["value"][1]))
        except (ValueError, KeyError, IndexError):
            continue
    
    return sum(cpu_values) / len(cpu_values) if cpu_values else 0.0

def get_memory_usage(namespace: str, deployment: str) -> float:
    """Get average memory usage in percentage"""
    promql = f'''
    avg(
      container_memory_working_set_bytes{{
        namespace="{namespace}",
        pod=~"{deployment}.*",
        container!="POD"
      }} / 
      container_spec_memory_limit_bytes{{
        namespace="{namespace}",
        pod=~"{deployment}.*",
        container!="POD"
      }}
    ) by (pod)
    '''
    
    results = query(promql)
    if not results:
        return 0.0
    
    memory_values = []
    for result in results:
        try:
            value = float(result["value"][1])
            if value <= 1.0:  # Ensure it's a ratio
                memory_values.append(value * 100)  # Convert to percentage
        except (ValueError, KeyError, IndexError):
            continue
    
    return sum(memory_values) / len(memory_values) if memory_values else 0.0

def get_request_rate(namespace: str, deployment: str) -> float:
    """Get HTTP request rate per second"""
    promql = f'''
    sum(
      rate(http_requests_total{{
        namespace="{namespace}",
        pod=~"{deployment}.*"
      }}[2m])
    )
    '''
    
    results = query(promql)
    if not results:
        # Try alternative metric name
        promql = f'''
        sum(
          rate(requests_total{{
            namespace="{namespace}",
            pod=~"{deployment}.*"
          }}[2m])
        )
        '''
        results = query(promql)
    
    if not results:
        return 0.0
    
    try:
        return float(results[0]["value"][1])
    except (ValueError, KeyError, IndexError):
        return 0.0

def get_latency_p95(namespace: str, deployment: str) -> float:
    """Get 95th percentile latency in seconds"""
    promql = f'''
    histogram_quantile(0.95,
      sum(
        rate(http_request_duration_seconds_bucket{{
          namespace="{namespace}",
          pod=~"{deployment}.*"
        }}[2m])
      ) by (le)
    )
    '''
    
    results = query(promql)
    if not results:
        return 0.0
    
    try:
        return float(results[0]["value"][1])
    except (ValueError, KeyError, IndexError):
        return 0.0

def get_all_metrics(namespace: str, deployment: str) -> Dict[str, float]:
    """Get all relevant metrics at once"""
    return {
        "cpu_usage": get_avg_cpu(namespace, deployment),
        "memory_usage": get_memory_usage(namespace, deployment),
        "request_rate": get_request_rate(namespace, deployment),
        "latency_p95": get_latency_p95(namespace, deployment)
    }
