from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import device_manager
import pyudev
import pprint
import requests
import subprocess

all_devices = []
all_devices_full_info = []
driver_name = "FT232"
api_url = 'http://localhost:5000/'

def get_all_devices():
    devices = []
    usb_devices = device_manager.list_usb_devices_with_driver(driver_name)
    if not usb_devices:
        print(f"No USB devices with driver '{driver_name}' found.")
    else:
        for device_info in usb_devices:
            product_descriptor, serial_number, device_path = device_info
            new_device = {"serial_num": serial_number, "path": device_path, "port": None,  "name": None, "baud": None }
            devices.append(new_device)
            
    return devices

def reload_devices():
    global all_devices
    all_devices = get_all_devices()
    
    # print(pprint.pformat(all_devices))
    # print("\n")
    send_devices()

def is_whole_usb_device(device):
    return device.get('DEVTYPE') == 'usb_device'

def handle_usb_event(action, device):
    reload_devices()
    if is_whole_usb_device(device):
        print(f"USB Device {action}: {device['DEVNAME']}")
        
        # handling code for USB device events
        send_devices()
        gen_yaml()

def monitor_usb_events():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')

    for action, device in monitor:
        handle_usb_event(action, device)

def send_devices():
    global all_devices_full_info
    serial_numbers = [d["serial_num"] for d in all_devices]
    response = requests.post(api_url + 'new-device', json=serial_numbers)
    all_devices_full_info = response.json()
    dict = {item['serial_num']: item for item in all_devices_full_info}

    # Update values in all_devices based on serial_number from updated
    for item in all_devices:
        serial_number = item['serial_num']
        if serial_number in dict:
            item.update(dict[serial_number])

def gen_yaml():
    file_path = '/etc/ser2net.yaml'
    config = ""
    for device in all_devices:
        none_values = [key for key, value in device.items() if value is None or value == -1]
        if none_values:
            continue

        config += f"""\
connection: &{device['name']}
    accepter: telnet,{device['port']}
    enable: on
    options:
        banner: {device['name']}
        kickolduser: true
        telnet-brk-on-sync: true
    connector: serialdev,
        {device['path']},
        {device['baud']}n81,local

"""
    with open(file_path, 'w') as file:
    # Write a string to the file
        file.write(config)
    
    result = subprocess.run("sudo systemctl restart ser2net", shell=True, capture_output=True, text=True)
    # result = subprocess.run("sudo ser2net -c /etc/ser2net.yaml", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("Command executed successfully.")
    else:
        print(f"Error: {result.stderr}")

############ Flask ############
app = Flask(__name__)
CORS(app)

@app.route('/update-devices', methods=['POST'])
def receive_data():
    global all_devices
    global all_devices_full_info
    data = request.json  # Assuming data is sent as JSON
    all_devices_full_info = data

    # modify to update list of
    dict = {item['serial_num']: item for item in data}

    # Update values in all_devices based on serial_number from updated
    for item in all_devices:
        serial_number = item['serial_num']
        if serial_number in dict:
            item.update(dict[serial_number])
    gen_yaml()

    # Process the received data and send a response
    response_data = {'message': 'Data received successfully'}
    return jsonify(response_data)


def run_flask():
    app.run(port=5001)
    
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    reload_devices()
    gen_yaml()
    monitor_usb_events()
