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

import subprocess
import os

init_script = './resources/scripts/init-device.sh'
get_onboarding_token_script = './resources/scripts/get-onboarding-token.sh'

def get_onboarding_token(device_id, gateway_id, keycloak_url, realm_password):
    arg1 = '-k'
    arg2 = keycloak_url
    arg3 = device_id
    arg4 = gateway_id
    subprocess.run([init_script, arg1, arg2, arg3, arg4], shell=False)

    arg1 = '-p'
    arg2 = realm_password
    arg3 = '-s'
    arg4 = './resources/' + 'devices-secret.yaml'
    arg5 = 'realm_user'
    subprocess.run([get_onboarding_token_script, arg1, arg2, arg3, arg4, arg5], shell=False)
