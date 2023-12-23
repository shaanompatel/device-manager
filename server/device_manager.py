import os
import serial.tools.list_ports

def find_usb_device_path_by_serial(serial_number):
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.serial_number == serial_number:
            return port.device
    return None

def list_usb_devices_with_driver(driver_name):
    usb_devices = []
    usb_device_path = '/sys/bus/usb/devices/'

    # Iterate through all USB devices in the sysfs
    for device in os.listdir(usb_device_path):
        try:
            with open(os.path.join(usb_device_path, device, 'product'), 'r') as product_file:
                product_descriptor = product_file.read().strip()

            # Check if the driver name is present in the product descriptor
            if driver_name in product_descriptor:
                with open(os.path.join(usb_device_path, device, 'serial'), 'r') as serial_file:
                    serial_number = serial_file.read().strip()
                
                device_path = find_usb_device_path_by_serial(serial_number)
                usb_devices.append((product_descriptor, serial_number, device_path))

        except Exception as e:
            pass

    return usb_devices

def device_not_duplicate(list, key, value):
    for device in list:
        if device[key] == value:
            return False
    return True

def synchronize_devices(all_devices, temp):
    # Update all_devices with elements from temp having a different "Serial Number"
    for temp_device in temp:
        temp_serial_number = temp_device.get("Serial Number")
        existing_device = next((device for device in all_devices if device.get("Serial Number") == temp_serial_number), None)
        if existing_device is None:
            all_devices.append(temp_device)
        else:
            existing_device.update(temp_device)

    # Remove elements from all_devices if their "Serial Number" is not in temp
    all_devices[:] = [device for device in all_devices if device.get("Serial Number") in {d.get("Serial Number") for d in temp}]

    return all_devices

if __name__ == "__main__":
    driver_name = "FT232"
    usb_devices = list_usb_devices_with_driver(driver_name)
    if not usb_devices:
        print(f"No USB devices with driver '{driver_name}' found.")
    else:
        print(f"USB devices with driver '{driver_name}':")
        for device_info in usb_devices:
            product_descriptor, serial_number, device_path = device_info
            print(f"Device: {product_descriptor}")
            print(f"Serial Number: {serial_number}")
            print(f"Device Path: {device_path}")
            print("---")
