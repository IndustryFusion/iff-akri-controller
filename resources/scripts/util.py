import subprocess
import os

init_script = './resources/scripts/init-device.sh'
get_onboarding_token_script = './resources/scripts/get-onboarding-token.sh'

def get_onboarding_token(device_id, gateway_id, protocol, keycloak_url, realm_password):
    arg1 = '-k'
    arg2 = keycloak_url
    arg3 = device_id
    arg4 = gateway_id
    subprocess.run([init_script, arg1, arg2, arg3, arg4], shell=False)

    arg1 = '-p'
    arg2 = realm_password
    arg3 = '-s'
    arg4 = './resources/' + protocol + '/' + 'devices-secret.yaml'
    arg5 = 'realm_user'
    subprocess.run([get_onboarding_token_script, arg1, arg2, arg3, arg4, arg5], shell=False)