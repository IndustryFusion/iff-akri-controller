// MongoDB Playground
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.

// The current database to use.
use('factory');

// Create a new document in the collection.
db.getCollection('onboardings').insertOne({
  "ip_address": "opcua://192.168.49.x:1212",
  "main_topic": "",
  "protocol": "mqtt",
  "app_config": {
    "fusiondataservice": {
      "custom_key": "custom_value",
      "specification": [
        {
          "topic": "airtracker-39B58/relay1",
          "key": [],
          "parameter": [
            "https://industry-fusion.org/base/v0.1/machine_state"
          ]
        },
        {
          "topic": "airtracker-39B58/dust",
          "key": [],
          "parameter": [
            "https://industry-fusion.org/base/v0.1/dustiness"
          ]
        },
        {
          "topic": "airtracker-39B58/temperature",
          "key": [],
          "parameter": [
            "https://industry-fusion.org/base/v0.1/temperature"
          ]
        },
        {
          "topic": "airtracker-39B58/humidity",
          "key": [],
          "parameter": [
            "https://industry-fusion.org/base/v0.1/humidity"
          ]
        },
        {
          "topic": "airtracker-39B58/noise",
          "key": [],
          "parameter": [
            "https://industry-fusion.org/base/v0.1/noise"
          ]
        }
      ]
    }
  },
  "pod_name": "airtrackertestcancom-mqtt",
  "pdt_mqtt_hostname": "devalerta.industry-fusion.com",
  "pdt_mqtt_port": 8883,
  "secure_config": true,
  "device_id": "urn:ifric:ifx-eur-nld-ast-567ca6bf-072d-56d9-adff-7529a09242ae",
  "gateway_id": "urn:ifric:ifx-eur-nld-ast-567ca6bf-072d-56d9-adff-7529a09242ae",
  "keycloak_url": "https://development.industry-fusion.com/auth/realms",
  "realm_password": "Abgp70pHTu2rP44IrouxImGkY0LM3P2T",
  "username_config": "mydeviceusername",
  "password_config": "mydevicepassword",
  "dataservice_image_config": "docker.io/ibn40/my-custom-data-service:latest",
  "agentservice_image_config": "docker.io/ibn40/iff-iot-agent:v0.0.4",
  "__v": 0
});
