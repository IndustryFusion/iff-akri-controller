import kopf
import logging
import os
import yaml
import kubernetes
import time

OISP_API_ROOT = os.environ.get('OISP_API_ROOT')


@kopf.on.create('Instance')
def create_fn_pod(spec, name, namespace, logger, **kwargs):
    time.sleep(1)

    if namespace == "devices":
        spec.get('brokerProperties').get('OPCUA_DISCOVERY_URL')
        

        data = yaml.safe_load(text)
            
        print(data)
        api = kubernetes.client.CoreV1Api()
        obj = api.patch_namespaced_secret(
            name=secret_name,
            namespace=namespace,
            body=data
        )

        logger.info(f"Token updated successfully: {obj}")