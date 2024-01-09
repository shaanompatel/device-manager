from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import pandas as pd
import threading
import device_manager
import subprocess
import pyudev

app = Flask(__name__)
CORS(app)

ATTRIBUTES = ["device_id", "name", "serial_num", "port", "baud"]
EDITABLE = ["name", "port", "baud"]

connected_devices = []

all_devices = []
all_devices_full_info = []

driver_name = "FT232"

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
    global connected_devices
    global all_devices_full_info

    connected_devices = [d["serial_num"] for d in all_devices]
    all_devices_full_info = fetch_devices()
    
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
    if result.returncode == 0:
        print("Command executed successfully.")
    else:
        print(f"Error: {result.stderr}")

### old ###

def create_server_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host = host_name,
            user = user_name,
            passwd = user_password,
            database = db_name
        )
        print(f"Successfully created database connection to '{db_name}'")
    except Error as err:
        print(f"Error: '{err}'")

    return connection

def query_database(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Successful database query")
    except Error as err:
        print(f"Error: '{err}'")

def read_query(connection, query):
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except Error as err:
        print(f"Error: '{err}'")

def update_entries(connection, table, data):
    for device in data:
        id = device['device_id']
        for attribute, value in device.items():
            if attribute in EDITABLE:
                query = f"""
                    UPDATE {table}
                    SET {attribute} = '{value}'
                    WHERE device_id = '{id}'
                    """
                query_database(connection, query)

def fetch_devices():
    from_db = []

    for device in connected_devices:
        info = read_query(connection, f"SELECT * FROM allDevices WHERE serial_num='{device}'")
        if not info:
            read_query(connection, f"INSERT INTO `allDevices` (`name`,`serial_num`,`port`,`baud`) VALUES ('unnamed','{device}',-1,-1);")
            info = read_query(connection, f"SELECT * FROM allDevices WHERE serial_num='{device}'")

        from_db.append(info[0])
    df = pd.DataFrame(from_db, columns=ATTRIBUTES)
    data_dict = df.to_dict(orient='records')
    data_dict = sorted(data_dict, key=lambda x: x['device_id'])
    return data_dict

connection = create_server_connection("localhost", "shaan", 'password', "devices")

############### API ################
@app.route('/health')
def check():
    return "OK"

@app.route('/api/get-devices')
def reload():
    return jsonify(fetch_devices())

@app.route('/api/edit', methods=['POST'])
def edit():
    global all_devices_full_info
    try:
        data = request.get_json()  # Get the JSON data from the request
        update_entries(connection, "allDevices", data)
        all_devices_full_info = fetch_devices() 
        return jsonify({'message': 'JSON received successfully', 'data': data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
def run_server():
    app.run(host='0.0.0.0')
 
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_server)
    flask_thread.start()
    reload_devices()
    gen_yaml()
    monitor_usb_events()
