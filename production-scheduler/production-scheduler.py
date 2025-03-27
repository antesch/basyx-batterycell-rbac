from flask import Flask, jsonify, Blueprint
import requests
import threading
import time
import os
from basyx.aas import model
from basyx.aas.adapter.json import AASFromJsonDecoder
import json
from typing import Dict
import base64
import uuid
import random
from collections import OrderedDict

product_scheduler_blueprint = Blueprint('product_scheduler', __name__, url_prefix='/product-scheduler')

# Configuration constants
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8081')
TOKEN_ENDPOINT = os.getenv('TOKEN_ENDPOINT', 'http://localhost:9097/realms/D4E/protocol/openid-connect/token')
print("token endpoint: " + str(TOKEN_ENDPOINT))
CLIENT_ID = os.getenv('CLIENT_ID', 'workstation-1')
CLIENT_SECRET = os.getenv('CLIENT_SECRET', 'nY0mjyECF60DGzNmQUjL81XurSl8etom')
PRODUCTION_DELAY = os.getenv('PRODUCTION_DELAY', '5')

# Constant dictionary for production steps. Key -> the name of the Process and Value -> the IdShort Path of the SME.
PRODUCTION_STEPS = OrderedDict([
    ("Material Preparation", "ProductionSteps%5B0%5D"),
    ("Electrode Fabrication", "ProductionSteps%5B1%5D"),
    ("Cell Assembly", "ProductionSteps%5B2%5D"),
    ("Electrolyte Filling", "ProductionSteps%5B3%5D"),
    ("Formation And Aging", "ProductionSteps%5B4%5D"),
])

AGGREGATED_PCF_PATH = "AggregatedCarbonFootprint"

PRODUCTION_STATUS: dict = {
    "NYP": "Not yet in Production",
    "IP": "In Production",
    "RFD": "Ready for Delivery"
}

PRODUCTION_STAGE: dict = {
    "P": "Pending",
    "I": "In Progress",
    "F": "Finished"
}

PRODUCTION_STEPS_PCF_EMISSION = OrderedDict([
    ("Material Preparation", 20),
    ("Electrode Fabrication", 10),
    ("Cell Assembly", 5),
    ("Electrolyte Filling", 2),
    ("Formation And Aging", 10),
])

ID_SHORT_LIST = ["CarbonFootprint", "Order", "ProductionPart"]

sm_dict: Dict[str, model.Submodel] = {}

# Token cache with timestamp for expiry tracking
token_cache = {'token': None, 'timestamp': None}

# Token expiry time in seconds (3 minutes)
TOKEN_EXPIRY_TIME = 3 * 60

# Method to check if the token is expired
def is_token_expired():
    if token_cache['timestamp'] is None:
        return True  # No token has been fetched yet
    current_time = time.time()
    return (current_time - token_cache['timestamp']) > TOKEN_EXPIRY_TIME

# Method to request a new token
def request_token():
    try:
        response = requests.post(TOKEN_ENDPOINT, data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials'
        })

        if response.status_code != 200:
            print(f"Error requesting token: {response.status_code} - {response.text}")
            return

        response_data = response.json()

        if 'access_token' not in response_data:
            print(f"Unexpected response format: {response_data}")
            return

        token_cache['token'] = response_data['access_token']
        token_cache['timestamp'] = time.time()
        print("Successfully retrieved a new token.")

    except Exception as e:
        print(f"Exception while requesting token: {str(e)}")
        
# Method to get the token
def get_bearer_token():
    if is_token_expired():
        print("Token expired or not found. Requesting a new one...")
        request_token()
    else:
        print("Using cached token.")
    return token_cache['token']

# Method to send a PATCH request with Bearer token
def send_patch_request(endpoint: str, data) -> requests.Response:
    headers = {
        'Authorization': f'Bearer {get_bearer_token()}',
        'Content-Type': 'application/json'
    }
    
    if isinstance(data, str):
        data_to_send = data
    else:
        data_to_send = json.dumps(data)
    response = requests.patch(f"{BASE_URL}/{endpoint}/$value", data=data_to_send, headers=headers)
    return response

def extract_ids_from_json(json_string: str, id_short_list: list) -> dict:
    data = json.loads(json_string)
    extracted_ids = {}
    
    id_short = data.get("idShort")
    id_value = data.get("id")
    
    if id_short in id_short_list and id_value:
        extracted_ids[id_short] = base64.b64encode(id_value.encode("utf-8")).decode()
    
    return extracted_ids

# Production process reset worker function
def reset_process(product_id: str, relevant_submodels: dict):

    # Iterate through all production steps
    for key, value in PRODUCTION_STEPS.items():
        
        send_patch_request(f"submodels/{relevant_submodels.get('ProductionPart')}/submodel-elements/{value}", f"\"{PRODUCTION_STAGE.get('P')}\"")
        
    send_patch_request(f"submodels/{relevant_submodels.get('CarbonFootprint')}/submodel-elements/{AGGREGATED_PCF_PATH}", f"\"0\"")

    # Log the completion of the process
    print(f"Product {product_id}: Production reset completed")

# Production process start worker function
def production_process(product_id: str, relevant_submodels: dict):

    # Change Production status to "In Production"
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/ProductionStatus", f"\"{PRODUCTION_STATUS.get('IP')}\"")
    print(f"Product {product_id}: Status updated to 'In Production'")
    
    cumulated_pcf = 0

    # Iterate through all production steps
    for key, value in PRODUCTION_STEPS.items():
        # Log the current production step
        print(f"Product {product_id}: Starting '{key}' stage")
        
        # Send PATCH request for production step
        send_patch_request(f"submodels/{relevant_submodels.get('ProductionPart')}/submodel-elements/{value}", f"\"{PRODUCTION_STAGE.get('I')}\"")
        
        # Wait for 10 seconds to simulate the production step
        wait_time()
        
        # Send PATCH request for production step
        send_patch_request(f"submodels/{relevant_submodels.get('ProductionPart')}/submodel-elements/{value}", f"\"{PRODUCTION_STAGE.get('F')}\"")
        print(f"Product {product_id}: Completed '{key}' stage")
        
        # Calculate and send dummy Product Carbon Footprint
        cumulated_pcf = cumulated_pcf + PRODUCTION_STEPS_PCF_EMISSION.get(key)
        send_patch_request(f"submodels/{relevant_submodels.get('CarbonFootprint')}/submodel-elements/{AGGREGATED_PCF_PATH}", f"\"{cumulated_pcf}\"")
        print(f"Product {product_id}: Updated Carbon Footprint after '{key}' stage: {cumulated_pcf}")

    # Update Production status to "Ready for Delivery"
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/ProductionStatus", f"\"{PRODUCTION_STATUS.get('RFD')}\"")
    print(f"Product {product_id}: Status updated to 'Ready for Delivery'")

    # Log the completion of the process
    print(f"Product {product_id}: Production process completed")

def wait_time():
    time.sleep(int(PRODUCTION_DELAY))
    
def update_initial_order_status(relevant_submodels: dict):
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/CustomerID", f"\"{uuid.uuid4()}\"")
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/OrderNumber", f"\"{uuid.uuid4()}\"")
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/OrderAmount", f"\"{random.randint(100, 1000)}\"")
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/TrackingNumber", f"\"{uuid.uuid4()}\"")
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/ProductionStatus", f"\"{PRODUCTION_STATUS.get('NYP')}\"")
    
def clear_initial_order_status(relevant_submodels: dict):
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/CustomerID", f"\"null\"")
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/OrderNumber", f"\"null\"")
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/OrderAmount", f"\"null\"")
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/TrackingNumber", f"\"null\"")
    send_patch_request(f"submodels/{relevant_submodels.get('Order')}/submodel-elements/ProductionStatus", f"\"{PRODUCTION_STATUS.get('NYP')}\"")

# Flask route to start the production process
@product_scheduler_blueprint.route('/start-production/<string:product_id>', methods=['POST'])
def start_production(product_id: str):
    
    decoded_bytes = base64.b64decode(product_id)

    decoded_product_id = decoded_bytes.decode("utf-8")
    
    token = get_bearer_token()
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Retrieve model from URL
    retries = 4
    for attempt in range(retries):
        model_response = requests.get(f"{BASE_URL}/shells/{product_id}", headers=headers)
        if model_response.status_code == 200:
            break
        time.sleep(2)  # Wait before retrying
    else:
        return jsonify({"error": "Failed to fetch model data after retries"}), 500
    model_data = model_response.text
    
    retrieved_model: model.AssetAdministrationShell = json.loads(model_data, cls=AASFromJsonDecoder)
    
    smref = []
    for ref in retrieved_model.submodel:
        key: model.Key = ref.key
        smref.append(key[0].value)
        
    relevant_submodels: dict = {}
    for sm_id in smref:
        sm_id_bytes = sm_id.encode("utf-8")
        model_response = requests.get(f"{BASE_URL}/submodels/{base64.b64encode(sm_id_bytes).decode()}", headers=headers)
        extracted_ids = extract_ids_from_json(model_response.text, ID_SHORT_LIST)
        if extracted_ids:
            relevant_submodels.update(extracted_ids)
    
    assert isinstance(retrieved_model, model.AssetAdministrationShell)
    
    wait_time()
    
    update_initial_order_status(relevant_submodels)

    # Start production process asynchronously
    thread = threading.Thread(target=production_process, args=(decoded_product_id, relevant_submodels))
    thread.start()

    return jsonify({"message": "Production process started", "product_id": decoded_product_id}), 202

# Flask route to reset the production process
@product_scheduler_blueprint.route('/reset-production/<string:product_id>', methods=['POST'])
def reset_production(product_id: str):
    
    decoded_bytes = base64.b64decode(product_id)

    decoded_product_id = decoded_bytes.decode("utf-8")
    
    token = get_bearer_token()
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Retrieve model from URL
    retries = 4
    for attempt in range(retries):
        model_response = requests.get(f"{BASE_URL}/shells/{product_id}", headers=headers)
        if model_response.status_code == 200:
            break
        time.sleep(2)  # Wait before retrying
    else:
        return jsonify({"error": "Failed to fetch model data after retries"}), 500
    model_data = model_response.text
    
    retrieved_model: model.AssetAdministrationShell = json.loads(model_data, cls=AASFromJsonDecoder)

    smref = []
    for ref in retrieved_model.submodel:
        key: model.Key = ref.key
        smref.append(key[0].value)
        
    relevant_submodels: dict = {}
    for sm_id in smref:
        sm_id_bytes = sm_id.encode("utf-8")
        model_response = requests.get(f"{BASE_URL}/submodels/{base64.b64encode(sm_id_bytes).decode()}", headers=headers)
        extracted_ids = extract_ids_from_json(model_response.text, ID_SHORT_LIST)
        if extracted_ids:
            relevant_submodels.update(extracted_ids)
    
    assert isinstance(retrieved_model, model.AssetAdministrationShell)
    
    clear_initial_order_status(relevant_submodels)

    # Start reset process asynchronously
    thread = threading.Thread(target=reset_process, args=(decoded_product_id, relevant_submodels))
    thread.start()

    return jsonify({"message": "Production process reset", "product_id": decoded_product_id}), 202

app = Flask(__name__)

app.register_blueprint(product_scheduler_blueprint)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)