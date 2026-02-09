from kubernetes import client, config

config.load_incluster_config()
apps = client.AppsV1Api()

def scale_deployment(namespace: str, name: str, replicas: int):
    body = {
        "spec": {
            "replicas": replicas
        }
    }

    apps.patch_namespaced_deployment_scale(
        name=name,
        namespace=namespace,
        body=body
    )

