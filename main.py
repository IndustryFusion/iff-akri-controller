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
from pymongo import MongoClient
import threading
from datetime import datetime

# Configure the logging
logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
kubernetes.config.load_incluster_config()  # or load_kube_config() for local dev
k8s = kubernetes.client.CustomObjectsApi()


resources = './resources'
# GitHub repository details
# owner = 'IndustryFusion'  # Replace with the repository owner's username
# repo = 'gateway-configs'  # Replace with the repository name
# path = ''  # Path within the repository (leave empty for the root directory)

# owner = os.environ.get("GITHUB_OWNER")
# repo = os.environ.get("GITHUB_REPO")
# path = os.environ.get("GITHUB_PATH") if os.environ.get("GITHUB_PATH") != '' else ''
# token = os.environ.get("GITHUB_TOKEN")
mongoUrl = os.environ.get("FACTORY_MONGO_URL")
mongoDbName = os.environ.get("FACTORY_MONGO_DB_NAME")
deviceId = os.environ.get("DEVICE_IFRIC_ID")
serverIp = os.environ.get("DEVICE_IP_ADDRESS")
# Replace with your MongoDB connection string
client = MongoClient(mongoUrl)
# headers = {'Authorization': 'Bearer ' + token, "Accept": "application/vnd.github+json" }

# # GitHub API URL for listing repository contents
# contents_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'

def start_mongo_stream_listener():
    last_check = {}  # Track last seen state for each document
    
    while True:
        try:
            collection = client[mongoDbName]["onboardings"]
            # Get current documents matching our device_id
            current_docs = list(collection.find({"device_id": deviceId}))
            current_ids = {str(doc['_id']): doc for doc in current_docs}
            
            # Check for new or updated documents
            for doc_id, doc in current_ids.items():
                doc_hash = hash(str(sorted(doc.items())))
                
                if doc_id not in last_check:
                    # New document - create CR
                    print(f"New document found: {doc_id}")
                    try:
                        k8s.create_namespaced_custom_object(
                            group="myorg.io",
                            version="v1",
                            namespace="devices",
                            plural="mongoinserts",
                            body={
                                "apiVersion": "myorg.io/v1",
                                "kind": "MongoInsert",
                                "metadata": {
                                    "name": "mongo-insert-" + doc_id
                                },
                                "spec": {
                                    "db": "factory",
                                    "collection": "onboardings",
                                    "document": doc_id
                                }
                            }
                        )
                        last_check[doc_id] = doc_hash
                    except kubernetes.client.exceptions.ApiException as e:
                        if e.status != 409:  # Ignore if already exists
                            print(f"Error creating CR: {e}")
                
                elif last_check[doc_id] != doc_hash:
                    # Document updated - patch CR
                    print(f"Document updated: {doc_id}")
                    try:
                        k8s.patch_namespaced_custom_object(
                            group="myorg.io",
                            version="v1",
                            namespace="devices",
                            plural="mongoinserts",
                            name="mongo-insert-" + doc_id,
                            body={
                                "spec": {
                                    "db": "factory",
                                    "collection": "onboardings",
                                    "document": doc_id + "-" + datetime.now().isoformat()
                                }
                            }
                        )
                        last_check[doc_id] = doc_hash
                    except kubernetes.client.exceptions.ApiException as e:
                        print(f"Error updating CR: {e}")
            
            # Check for deleted documents
            for doc_id in list(last_check.keys()):
                if doc_id not in current_ids:
                    print(f"Document deleted: {doc_id}")
                    try:
                        k8s.delete_namespaced_custom_object(
                            group="myorg.io",
                            version="v1",
                            namespace="devices",
                            plural="mongoinserts",
                            name="mongo-insert-" + doc_id
                        )
                        del last_check[doc_id]
                    except kubernetes.client.exceptions.ApiException as e:
                        if e.status != 404:  # Ignore if already deleted
                            print(f"Error deleting CR: {e}")
            
        except Exception as e:
            print(f"Polling failed: {e}, retrying in 10 seconds...")
        
        time.sleep(10)  # Poll every 10 seconds


@kopf.on.startup()
def startup_fn(logger, **_):
    logger.info("Kopf operator started and listening.")
    thread = threading.Thread(target=start_mongo_stream_listener, daemon=True)
    thread.start()
    
    # Trigger updates on restart by patching existing CRs with a timestamp annotation
    try:
        logger.info("Checking for existing CRs to trigger updates on restart...")
        existing_crs = k8s.list_namespaced_custom_object(
            group="myorg.io",
            version="v1",
            namespace="devices",
            plural="mongoinserts"
        )
        
        restart_timestamp = datetime.now().isoformat()
        for cr in existing_crs.get('items', []):
            cr_name = cr['metadata']['name']
            try:
                logger.info(f"Triggering update for CR: {cr_name}")
                k8s.patch_namespaced_custom_object(
                    group="myorg.io",
                    version="v1",
                    namespace="devices",
                    plural="mongoinserts",
                    name=cr_name,
                    body={
                        "metadata": {
                            "annotations": {
                                "controller-restart-trigger": restart_timestamp
                            }
                        }
                    }
                )
                logger.info(f"Successfully triggered update for CR: {cr_name}")
            except Exception as e:
                logger.error(f"Failed to update CR {cr_name}: {e}")
    except Exception as e:
        logger.error(f"Failed to list existing CRs: {e}")


@kopf.on.create('myorg.io', 'v1', 'mongoinserts')
def create_fn_pod(name, namespace, logger, **kwargs):
    time.sleep(1)
    logger.info(f"Creating pod {name} in namespace {namespace}")

    if namespace == "devices":
        collection = client[mongoDbName]["onboardings"]
        documents = list(collection.find({"gateway_id": deviceId}, {"_id": 0}))
        PLACEHOLDER = 'akri.sh/' + name
        
        # Make a request to get the repository contents
        # response = requests.get(contents_url, headers=headers)
        # response.raise_for_status()  # Raise an error if the request failed

        # kopf.info("Initial response from GitHub GW config contents" + str(response), reason='SomeReason')
        # kopf.info("IP from Akri" + str(ip_from_akri), reason='SomeReason')

        if len(documents) != 0:
            for file_info in documents:
                    # Get the file's download URL
                    # file_url = file_info['download_url']
                    
                    # # Make a request to get the file contents
                    # file_response = requests.get(file_url)
                    # file_response.raise_for_status()
                
                logger.info(f"Document of Mongo: {file_info}")
                config_data = yaml.safe_load(yaml.dump(file_info))

                logger.info(f"Config Data from Mongo: {config_data}")
                logger.info(f"IP address in Config from Mongo: {config_data['ip_address']}")
                # kopf.info("Config Data from GitHub" + str(config_data), reason='SomeReason')
                # kopf.info("IP address in Config from GitHub" + str(config_data['ip_address']), reason='SomeReason')

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
                    formatted_yaml = edit_data.replace('pod_name', config_data['pod_name']).replace('url_config', str(config_data['ip_address'])).replace('username_config', str(config_data['username_config'])).replace('password_config', str(config_data['password_config'])).replace(
                                            'dataservice_image_config', config_data['dataservice_image_config']).replace(
                                            'agentservice_image_config', config_data['agentservice_image_config']).replace('server_ip', serverIp)
                    
                    body_data=yaml.safe_load(formatted_yaml)
                    kopf.adopt(body_data)

                    api = kubernetes.client.AppsV1Api()
                    obj = api.create_namespaced_deployment(
                        namespace=namespace,
                        body=body_data
                    )

                    logger.info(f"Data Service Deployment created successfully: {obj}")
        else:
            logger.info(f"No deployment queue file found in the aggregation location")


@kopf.on.update('myorg.io', 'v1', 'mongoinserts')    
def update_fn_pod(name, namespace, logger, **kwargs):
    time.sleep(1)
    logger.info(f"Update triggered for {name}. Recreating dependent resources...")

    if namespace == "devices":
        # Call the delete logic
        delete_fn_pod(name=name, namespace=namespace, logger=logger, **kwargs)

        # Sleep briefly to avoid race conditions (optional but helpful)
        time.sleep(60)

        # Call the create logic
        create_fn_pod(name=name, namespace=namespace, logger=logger, **kwargs)

        logger.info(f"Update finished for {name}.")


@kopf.on.delete('myorg.io', 'v1', 'mongoinserts')    
def delete_fn_pod(name, namespace, logger, **kwargs):
    time.sleep(1)
    logger.info(f"Creating pod {name} in namespace {namespace}")

    if namespace == "devices":
        collection = client[mongoDbName]["onboardings"]
        documents = list(collection.find({"gateway_id": deviceId}, {"_id": 0}))
        if len(documents) != 0:
            for file_info in documents:
                logger.info(f"Document of Mongo: {file_info}")
                config_data = yaml.safe_load(yaml.dump(file_info))

                try:
                    api = kubernetes.client.CoreV1Api()
                    api.delete_namespaced_config_map(
                        name=config_data['pod_name'] + "-app-config",
                        namespace=namespace,
                        body=kubernetes.client.V1DeleteOptions()
                    )
                    api.delete_namespaced_config_map(
                        name=config_data['pod_name'] + "-global-devices-config",
                        namespace=namespace,
                        body=kubernetes.client.V1DeleteOptions()
                    )
                    api.delete_namespaced_config_map(
                        name=config_data['pod_name'] + "-devices-data-config",
                        namespace=namespace,
                        body=kubernetes.client.V1DeleteOptions()
                    )
                    api2 = kubernetes.client.AppsV1Api()
                    api2.delete_namespaced_deployment(
                        name=config_data['pod_name'],
                        namespace=namespace,
                        body=kubernetes.client.V1DeleteOptions()
                    )
                    logger.info(f"ConfigMaps deleted.")
                except kubernetes.client.exceptions.ApiException as e:
                    if e.status == 404:
                        logger.warning(f"Not found, skipping delete.")
                    else:
                        raise