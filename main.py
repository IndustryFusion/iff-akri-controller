import kopf
import logging
import json
import os
import yaml
import kubernetes
import time
import subprocess
from resources.scripts.util import get_onboarding_token

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

        for file in os.listdir(yaml_config_file_path):
            file_path = os.path.join(yaml_config_file_path, file)

            with open(file_path, 'r') as config_file:
                config_data = yaml.safe_load(config_file)

            for item in config_data['ip_address']:
                if item in ip_from_akri:
                    if config_data['protocol'] == 'opcua':
                        with open(resources + config_data['protocol'] + '/app-config.yaml', 'r') as edit_file:
                            edit_data = edit_file.read()
                            formatted_yaml = edit_data.format(app_config=config_data['app_config'], pod_name=config_data['pod_name'])
                            body_data = yaml.safe_load(formatted_yaml)
                            kopf.adopt(body_data)
                            api = kubernetes.client.CoreV1Api()
                            obj = api.create_namespaced_config_map(
                                namespace=namespace,
                                body=body_data,
                            )
                            logger.info(f"App config created successfully: {obj}")

                        # with open(resources + config_data['protocol'] + '/deployment.yaml', 'r') as edit_file:
                        #     edit_data = edit_file.read()
                        #     formatted_yaml = edit_data.format(
                        #         pod_name=config_data['pod_name'])
                        #     # print(formatted_yaml)

                        # with open(resources + config_data['protocol'] + '/devices-config.yaml', 'r') as edit_file:
                        #     edit_data = edit_file.read()
                        #     formatted_yaml = edit_data.replace('pdt_hostname', config_data['pdt_hostname']).replace(
                        #         'pdt_mqtt_port', config_data['pdt_mqtt_port']).replace('pod_name', config_data['pod_name'])
                        #     # print(formatted_yaml)

                        # get_onboarding_token(
                        #     config_data['device_id'], config_data['gateway_id'], config_data['protocol'])
                        # with open(resources + config_data['protocol'] + '/devices-secret.yaml', 'r') as edit_file:
                        #     print('')

                        # with open('./data/device.json') as device_file:
                        #     device_data = device_file.read()
                        # with open(resources + config_data['protocol'] + '/devices-data-config.yaml', 'r') as edit_file:
                        #     edit_data = edit_file.read()
                        #     formatted_yaml = edit_data.format(
                        #         device_json=device_data, pod_name=config_data['pod_name'])
                        #     print(formatted_yaml)

                        # with open(resources + config_data['protocol'] + '/service-account.yaml', 'r') as edit_file:
                        #     edit_data = edit_file.read()
                        #     # print(formatted_yaml)