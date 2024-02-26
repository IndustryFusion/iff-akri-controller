import subprocess
import os

init_script = './resources/scripts/init-device.sh'
get_onboarding_token_script = './resources/scripts/get-onboarding-token.sh'

def get_onboarding_token(device_id, gateway_id, protocol):
    arg1 = '-k https://development.industry-fusion.com/auth/realms'
    arg2 = device_id
    arg3 = gateway_id
    # Execute the shell script with arguments
    # When using shell=True, combine the script path and arguments into a single string
    result = subprocess.run(f'{init_script} {arg1} {arg2} {arg3}', capture_output=True, text=True, shell=True)

    # Access the return code, stdout, and stderr
    print('Return code:', result.returncode)
    print('stdout:', result.stdout)
    print('stderr:', result.stderr)

    arg1 = '-p KFrqIcPfeC4zRFmQs3rJpZgszaJjOxet'
    arg2 = '-s ' + './resources/' + protocol + '/' + 'devices-secret.yaml'
    arg3 = 'realm_user'
    result = subprocess.run(f'{get_onboarding_token_script} {arg1} {arg2} {arg3}', capture_output=True, text=True, shell=True)

    # Access the return code, stdout, and stderr
    print('Return code:', result.returncode)
    print('stdout:', result.stdout)
    print('stderr:', result.stderr)