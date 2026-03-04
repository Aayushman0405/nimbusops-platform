import requests
import os
from typing import List, Dict, Any
import time

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
    except requests.exceptions.ConnectionError:
        print(f"[Prometheus] Connection error - is Prometheus running at {PROM_URL}?")
        return []
    except Exception as e:
        print(f"[Prometheus] Query failed: {e}")
        return []

def get_avg_cpu(namespace: str, deployment: str) -> float:
    """Get average CPU usage for deployment"""
    # Try different container name patterns
    promql_variations = [
        f'''
        avg(
          rate(container_cpu_usage_seconds_total{{
            namespace="{namespace}",
            pod=~"{deployment}.*",
            container!="POD",
            container!=""
          }}[2m])
        )
        ''',
        f'''
        avg(
          rate(container_cpu_usage_seconds_total{{
            namespace="{namespace}",
            pod=~"{deployment}.*"
          }}[2m])
        ) by (pod)
        ''',
        # Fallback to node-exporter metrics
        f'''
        sum(
          rate(node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate{{
            namespace="{namespace}",
            pod=~"{deployment}.*"
          }}[2m])
        )
        '''
    ]
    
    for promql in promql_variations:
        results = query(promql)
        if results:
            try:
                # Handle different result formats
                if isinstance(results, list):
                    if len(results) == 0:
                        continue
                    if "value" in results[0]:
                        return float(results[0]["value"][1])
                    elif "values" in results[0]:
                        return float(results[0]["values"][-1][1])
                elif isinstance(results, dict):
                    return float(results.get("value", [0, 0])[1])
            except (ValueError, KeyError, IndexError, TypeError):
                continue
    
    return 0.0

def get_memory_usage(namespace: str, deployment: str) -> float:
    """Get average memory usage in percentage"""
    promql = f'''
    avg(
      container_memory_working_set_bytes{{
        namespace="{namespace}",
        pod=~"{deployment}.*",
        container!="POD"
      }} /
      kube_pod_container_resource_limits{{
        namespace="{namespace}",
        pod=~"{deployment}.*",
        resource="memory"
      }}
    )
    '''

    results = query(promql)
    if not results:
        return 0.0

    try:
        if results and "value" in results[0]:
            value = float(results[0]["value"][1])
            return value * 100  # Convert to percentage
    except (ValueError, KeyError, IndexError):
        pass

    return 0.0

def get_request_rate(namespace: str, deployment: str) -> float:
    """Get HTTP request rate per second"""
    # Try to get request rate from inference service
    promql_variations = [
        f'''
        sum(
          rate(nginx_ingress_controller_requests{{
            namespace="{namespace}",
            ingress=~".*inference.*"
          }}[2m])
        )
        ''',
        f'''
        sum(
          rate(container_network_receive_bytes_total{{
            namespace="{namespace}",
            pod=~"{deployment}.*"
          }}[2m])
        ) / 1024  # Convert to KB/s
        ''',
        f'''
        sum(
          rate(istio_requests_total{{
            destination_service_namespace="{namespace}",
            destination_service_name=~".*inference.*"
          }}[2m])
        )
        '''
    ]

    for promql in promql_variations:
        results = query(promql)
        if results:
            try:
                if results and "value" in results[0]:
                    return float(results[0]["value"][1])
            except (ValueError, KeyError, IndexError):
                continue

    return 0.0

def get_latency_p95(namespace: str, deployment: str) -> float:
    """Get 95th percentile latency in seconds"""
    promql = f'''
    histogram_quantile(0.95,
      sum(
        rate(istio_request_duration_milliseconds_bucket{{
          destination_service_namespace="{namespace}",
          destination_service_name=~".*inference.*"
        }}[2m])
      ) by (le)
    ) / 1000  # Convert to seconds
    '''

    results = query(promql)
    if not results:
        return 0.0

    try:
        if results and "value" in results[0]:
            return float(results[0]["value"][1])
    except (ValueError, KeyError, IndexError):
        pass

    return 0.0

def get_all_metrics(namespace: str, deployment: str) -> Dict[str, float]:
    """Get all relevant metrics at once"""
    return {
        "cpu_usage": get_avg_cpu(namespace, deployment),
        "memory_usage": get_memory_usage(namespace, deployment),
        "request_rate": get_request_rate(namespace, deployment),
        "latency_p95": get_latency_p95(namespace, deployment)
    }

def check_prometheus_health() -> bool:
    """Check if Prometheus is reachable"""
    try:
        resp = requests.get(f"{PROM_URL}/-/healthy", timeout=5)
        return resp.status_code == 200
    except:
        return False
