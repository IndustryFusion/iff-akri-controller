import kopf
import logging
import json
import os
import yaml
import kubernetes
import time
import subprocess
from resources.scripts.util import get_onboarding_token

logging.basicConfig(level=logging.DEBUG)
yaml_config_file_path = './resources/test-configs/'
resources = './resources/'
# ip_from_akri = '192.168.49.194'
# selected_config_file_path = ''

# OISP_API_ROOT = os.environ.get('OISP_API_ROOT')


@kopf.on.create('Instance')
def create_fn_pod(spec, name, namespace, logger, **kwargs):
    time.sleep(1)

    if namespace == "devices":
        ip_from_akri = spec.get('brokerProperties').get('OPCUA_DISCOVERY_URL')
        PLACEHOLDER = 'akri.sh/' + name
        for file in os.listdir(yaml_config_file_path):
            file_path = os.path.join(yaml_config_file_path, file)

            with open(file_path, 'r') as config_file:
                config_data = yaml.safe_load(config_file)

            for item in config_data['ip_address']:
                if item in ip_from_akri:
                    if config_data['protocol'] == 'opcua':
                        # with open(resources + config_data['protocol'] + '/app-config.yaml', 'r') as edit_file:
                        #     edit_data = edit_file.read()
                            # formatted_yaml = edit_data.replace('app_config', json.dumps(config_data['app_config'])).replace('pod_name', config_data['pod_name'])
                            
                            # Create a ConfigMap object
                        config_map = kubernetes.client.V1ConfigMap(
                            api_version="v1",
                            kind="ConfigMap",
                            metadata=kubernetes.client.V1ObjectMeta(name=config_data['pod_name'] + "-app-config"),
                            data={"config.json": config_data['app_config']}
                        )

                        kopf.adopt(config_map)

                        api = kubernetes.client.CoreV1Api()
                        obj = api.create_namespaced_config_map(
                            namespace=namespace,
                            body=config_map
                        )

                        logger.info(f"App config created successfully: {obj}")

                        with open(resources + config_data['protocol'] + '/devices-config.yaml', 'r') as edit_file:
                            edit_data = edit_file.read()
                            formatted_yaml = edit_data.replace('pdt_mqtt_hostname', config_data['pdt_mqtt_hostname']).replace(
                                'pdt_mqtt_port', config_data['pdt_mqtt_port']).replace('pod_name', config_data['pod_name']).replace('secure_config', config_data['secure_config'])
                            
                            body_data=yaml.safe_load(formatted_yaml)
                            kopf.adopt(body_data)

                            api = kubernetes.client.CoreV1Api()
                            obj = api.create_namespaced_config_map(
                                namespace=namespace,
                                body=body_data
                            )

                            logger.info(f"Global devices config created successfully: {obj}")


                        get_onboarding_token(
                            config_data['device_id'], config_data['gateway_id'], config_data['protocol'], config_data['keycloak_url'], config_data['realm_password'])
                        # logger.info(f"The subprocess status: {status}")
                        with open(resources + config_data['protocol'] + '/devices-secret.yaml', 'r') as edit_file:
                            edit_data = edit_file.read()
                            body_data=yaml.safe_load(edit_data)
                            kopf.adopt(body_data)

                            api = kubernetes.client.CoreV1Api()
                            obj = api.create_namespaced_secret(
                                namespace=namespace,
                                body=body_data
                            )

                            logger.info(f"Onboarding secret created successfully: {obj}")
                        
                        with open('./data/device.json') as device_file:
                            device_data = device_file.read()
                            
                            config_map = kubernetes.client.V1ConfigMap(
                                api_version="v1",
                                kind="ConfigMap",
                                metadata=kubernetes.client.V1ObjectMeta(name=config_data['pod_name'] + "-devices-data-config"),
                                data={"device.json": device_data}
                            )

                            kopf.adopt(config_map)

                            api = kubernetes.client.CoreV1Api()
                            obj = api.create_namespaced_config_map(
                                namespace=namespace,
                                body=config_map
                            )

                            logger.info(f"Device congfig created successfully: {obj}")

                        with open(resources + config_data['protocol'] + '/deployment.yaml', 'r') as edit_file:
                            edit_data = edit_file.read()
                            formatted_yaml = edit_data.replace('pod_name', config_data['pod_name']).replace('pdt_mqtt_hostname', config_data['pdt_mqtt_hostname']).replace('PLACEHOLDER', PLACEHOLDER)
                            
                            body_data=yaml.safe_load(formatted_yaml)
                            kopf.adopt(body_data)

                            api = kubernetes.client.AppsV1Api()
                            obj = api.create_namespaced_deployment(
                                namespace=namespace,
                                body=body_data
                            )

                            logger.info(f"Deployment created successfully: {obj}")