from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import pandas as pd
import requests


app = Flask(__name__)
CORS(app)

ATTRIBUTES = ["device_id", "name", "serial_num", "port", "baud"]
EDITABLE = ["name", "serial_num", "port", "baud"]

connected_devices = []

server_url = 'http://localhost:5001/update-devices'

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
                # print(f"   {attribute} : {value}")
                query = f"""
                    UPDATE {table}
                    SET {attribute} = '{value}'
                    WHERE device_id = '{id}'
                    """
                query_database(connection, query)

def fetch_devices():
    # here - scan for new USB devices and add them to the the table, don't fetch ones that are in the database but not connected
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
    try:
        data = request.get_json()  # Get the JSON data from the request
        update_entries(connection, "allDevices", data)
        response = requests.post(server_url, json=fetch_devices())
        print(response.text)
        return jsonify({'message': 'JSON received successfully', 'data': data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/new-device', methods=['POST'])
def update_device_list():
    global connected_devices
    try:
        data = request.get_json()
        connected_devices = list(data)
        return jsonify(fetch_devices())
    except Exception as e:
        return jsonify({'error': str(e)}), 400
 
if __name__ == '__main__':
    app.run(host='0.0.0.0')
