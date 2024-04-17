#
# Copyright (c) 2024 IB Systems GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

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
# owner = 'IndustryFusion'  # Replace with the repository owner's username
# repo = 'gateway-configs'  # Replace with the repository name
# path = ''  # Path within the repository (leave empty for the root directory)

owner = os.environ.get("GITHUB_OWNER")
repo = os.environ.get("GITHUB_REPO")
path = os.environ.get("GITHUB_PATH") if os.environ.get("GITHUB_PATH") != '' else ''
token = os.environ.get("GITHUB_OWNER")

headers = {'Authorization': 'token ' + token }
# GitHub API URL for listing repository contents
contents_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'


@kopf.on.create('Instance')
@kopf.on.resume('Instance')
def create_fn_pod(spec, name, namespace, logger, **kwargs):
    time.sleep(1)

    if namespace == "devices":
        if 'opc' in name:
            ip_from_akri = spec.get('brokerProperties').get('OPCUA_DISCOVERY_URL')
        elif 'mqtt' in name:
            ip_from_akri = spec.get('brokerProperties').get('MQTT_BROKER_URI')
            main_mqtt_topic = spec.get('brokerProperties').get('MQTT_TOPIC')

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
                        if config_data['protocol'] == 'opcua' or config_data['protocol'] == 'mqtt' and config_data['main_topic'] == main_mqtt_topic:

                            config_map = kubernetes.client.V1ConfigMap(
                                api_version="v1",
                                kind="ConfigMap",
                                metadata=kubernetes.client.V1ObjectMeta(name=config_data['pod_name'] + "-app-config"),
                                data={"config.yaml": str(config_data['app_config'])}
                            )

                            kopf.adopt(config_map)

                            api = kubernetes.client.CoreV1Api()
                            obj = api.create_namespaced_config_map(
                                namespace=namespace,
                                body=config_map
                            )

                            logger.info(f"App config created successfully: {obj}")

                            with open(resources + '/devices-config.yaml', 'r') as edit_file:
                                edit_data = edit_file.read()
                                formatted_yaml = edit_data.replace('pdt_mqtt_hostname', config_data['pdt_mqtt_hostname']).replace(
                                    'pdt_mqtt_port', str(config_data['pdt_mqtt_port'])).replace('secure_config', str(config_data['secure_config']).lower()).replace('pod_name', config_data['pod_name'])
                                
                                body_data=yaml.safe_load(formatted_yaml)
                                kopf.adopt(body_data)

                                api = kubernetes.client.CoreV1Api()
                                obj = api.create_namespaced_config_map(
                                    namespace=namespace,
                                    body=body_data
                                )

                                logger.info(f"Global devices config created successfully: {obj}")


                            get_onboarding_token(
                                config_data['device_id'], config_data['gateway_id'], config_data['keycloak_url'], config_data['realm_password'])
                            
                            with open(resources + '/devices-secret.yaml', 'r') as edit_file:
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

                            with open(resources + '/deployment.yaml', 'r') as edit_file:
                                edit_data = edit_file.read()
                                formatted_yaml = edit_data.replace('pod_name', config_data['pod_name']).replace(
                                        'PLACEHOLDER', PLACEHOLDER).replace('username_config', str(config_data['username_config'])).replace('password_config', str(config_data['password_config'])).replace(
                                                        'dataservice_image_config', config_data['dataservice_image_config']).replace(
                                                        'agentservice_image_config', config_data['agentservice_image_config'])
                                
                                body_data=yaml.safe_load(formatted_yaml)
                                kopf.adopt(body_data)

                                api = kubernetes.client.AppsV1Api()
                                obj = api.create_namespaced_deployment(
                                    namespace=namespace,
                                    body=body_data
                                )

                                logger.info(f"Data Service Deployment created successfully: {obj}")
                        else:
                            logger.info(f"Searching gateway config files")
                    else:
                        logger.info(f"Searching gateway config files")
                else:
                    logger.info(f"No files found in root of GitHub repo")
        else:
            logger.info(f"No deployment queue file found in the aggregation location")
