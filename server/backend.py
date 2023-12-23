import device_manager
import pyudev
import usb.util
import pprint
import yaml
import json
import requests

all_devices = []
driver_name = "FT232"
api_url = 'http://localhost:5000/new-device'

def get_all_devices():
    devices = []
    usb_devices = device_manager.list_usb_devices_with_driver(driver_name)
    print(len(usb_devices))
    if not usb_devices:
        print(f"No USB devices with driver '{driver_name}' found.")
    else:
        #print(f"USB devices with driver '{driver_name}':")
        for device_info in usb_devices:
            product_descriptor, serial_number, device_path = device_info
            new_device = {"Serial Number": serial_number, "Path": device_path, "Binding": None}
            
            #if device_manager.device_not_duplicate(all_devices, "Serial Number", new_device["Serial Number"]):
            devices.append(new_device)
                
            #print(f"Device: {product_descriptor}")
            #print(f"Serial Number: {serial_number}")
            #print(f"Device Path: {device_path}")
            #print("---")
    return devices

def reload_devices():
    global all_devices
    temp = get_all_devices()
    all_devices = temp
    # device_manager.synchronize_devices(all_devices, temp)
    print(pprint.pformat(all_devices))
    print("\n")
    send_devices()

def is_whole_usb_device(device):
    return device.get('DEVTYPE') == 'usb_device'

def handle_usb_event(action, device):
    reload_devices()
    if is_whole_usb_device(device):
        print(f"USB Device {action}: {device['DEVNAME']}")
        # Add your handling code here for USB device events
        send_devices()

def monitor_usb_events():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')

    for action, device in monitor:
        handle_usb_event(action, device)

def send_devices():
    # print(all_devices)
    # reload_devices()
    serial_numbers = [d["Serial Number"] for d in all_devices]
    response = requests.post(api_url, json=serial_numbers)
    print("Response:", response.text)
    
if __name__ == "__main__":
    reload_devices()
    # send_devices()
    monitor_usb_events()


""" def gen_yaml():
    file_path = 'testconf.yaml'
    with open(file_path, 'w') as file:
        for device in all_devices:
            connection = {
                'accepter': f'tcp,{device["Binding"]}',
                'enable': 'on',
                'options': {
                    'banner': '<<banner_variable>>',
                    'kickolduser': True,
                    'telnet-brk-on-sync': True
            },
            'connector': [
                'serialdev',
                f'{device["Path"]}',
                '115200n81',
                'local'
            ]
            }
            
            data = {
                'connection': connection
            }
            
            yaml_data = yaml.dump(data, file)
            file.write('\n---\n')  # Add a new line between each entry """