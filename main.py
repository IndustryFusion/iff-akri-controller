import kopf
import logging
import json
import os
import yaml
import kubernetes
import time
import subprocess
from resources.scripts.util import get_onboarding_token
import requests

logging.basicConfig(level=logging.DEBUG)

resources = './resources/'
# GitHub repository details
owner = 'IndustryFusion'  # Replace with the repository owner's username
repo = 'gateway-configs'  # Replace with the repository name
path = ''  # Path within the repository (leave empty for the root directory)

headers = {'Authorization': 'token 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'}
# GitHub API URL for listing repository contents
contents_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'


@kopf.on.create('Instance')
@kopf.on.resume('Instance')
def create_fn_pod(spec, name, namespace, logger, **kwargs):
    time.sleep(1)

    if namespace == "devices":
        ip_from_akri = spec.get('brokerProperties').get('OPCUA_DISCOVERY_URL')
        ip_from_akri = str(ip_from_akri).split('//')[1].split(':')[0]
        PLACEHOLDER = 'akri.sh/' + name
        
        # Make a request to get the repository contents
        response = requests.get(contents_url, headers=headers)
        response.raise_for_status()  # Raise an error if the request failed

        if len(response.json()) != 0:
            for file_info in response.json():
                if file_info['type'] == 'file':
                    # Get the file's download URL
                    file_url = file_info['download_url']
                    
                    # Make a request to get the file contents
                    file_response = requests.get(file_url)
                    file_response.raise_for_status()

                    config_data = yaml.safe_load(file_response.text)

                    if str(config_data['ip_address']) == str(ip_from_akri):
                        if config_data['protocol'] == 'opcua':
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
                        else:
                            logger.info(f"Only opcua is currently supported for protocol value")
                    else:
                        logger.info(f"Searching gateway config files")
                else:
                    logger.info(f"No files found in root of GitHub repo")
        else:
            logger.info(f"No deployment queue file found in the aggregation location")