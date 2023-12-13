import subprocess
import re
import json
import os

# Function to extract and save active network connections for specific hosts
def extract_and_save_peer_connections():
    # Run netstat command to get network connections and capture its output
    result = subprocess.run(["netstat", "-ntu"], capture_output=True, text=True)
    netstat_output = result.stdout

    # Regular expression to find IP addresses and ports in netstat output
    ip_port_regex = r'(\d+\.\d+\.\d+\.\d+):(\d+)'

    # Specific hosts to filter for, This IP addresses need to include in the code.
    specific_hosts = ['192.168.88.72', '192.168.88.69']

    # Use regex to find all matches in netstat output
    matches = re.findall(ip_port_regex, netstat_output)

    # Filter matches for specific hosts and ports with more than 3 digits
    connections = [{'ip': match[0], 'port': match[1]} for match in set(matches) if len(match[1]) > 3 and match[0] in specific_hosts]

    # Save filtered connections to a JSON file
    with open('ip.json', 'w') as file:
        json.dump(connections, file, indent=4)

    # Print the number of saved connections
    print(f"Saved {len(connections)} connections for specified hosts to ip.json")

# Function to check if a specific module is loaded in the system
def is_module_loaded(module_name):
    # Run lsmod to list loaded modules and capture output
    result = subprocess.run(['lsmod'], capture_output=True, text=True)

    # Check if the specified module is in the output
    if module_name in result.stdout:
        return True

    # Try to load the module using modprobe if not already loaded
    try:
        subprocess.run(['sudo', 'modprobe', module_name], check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to load module {module_name}")
        return False

# Function to check if a network interface is present
def is_interface_present(interface_name):
    # Check if the specified network interface exists using 'ip link show'
    result = subprocess.run(['ip', 'link', 'show', interface_name], capture_output=True)

    if result.returncode == 0:
        return True

    # If interface does not exist, try to add it
    try:
        subprocess.run(['sudo', 'ip', 'link', 'add', 'name', interface_name, 'type', 'ifb'], check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to add interface {interface_name}")
        return False

# Function to set up network traffic control environment
def setup_environment(speed, latency):
    # Add ingress queueing discipline and filter to wlan0 interface
    os.system("sudo tc qdisc add dev wlan0 handle ffff: ingress")
    os.system("sudo tc filter add dev wlan0 parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0")

    # Add HTB (Hierarchical Token Bucket) qdisc and netem qdisc to ifb0
    os.system(f"sudo tc qdisc add dev ifb0 root handle 1: htb default 30")
    os.system(f"sudo tc class add dev ifb0 parent 1: classid 1:1 htb rate {speed}kbit")
    os.system(f"sudo tc qdisc add dev ifb0 parent 1:1 handle 10: netem latency {latency}ms")

# Function to apply throttling to a specific IP and port
def apply_throttling(ip, port, speed):
    # Add filter to ifb0 for matching specified port and redirecting traffic to a specific class with speed limit
    os.system(f"sudo tc filter add dev ifb0 protocol ip parent 1: prio 1 u32 match ip dport {port} 0xffff flowid 1:1")

# Function to clear all traffic control settings
def clear_throttling():
    # Remove ingress and egress queueing disciplines from interfaces
    os.system("sudo tc qdisc del dev wlan0 handle ffff: ingress")
    os.system("sudo tc qdisc del dev ifb0 root")

# Function to read and return the content of a JSON file
def read_json_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)

# Function to check if darkstat network monitoring tool is installed
def is_darkstat_installed():
    return subprocess.run(['which', 'darkstat'], stdout=subprocess.DEVNULL).returncode == 0

# Function to install darkstat
def install_darkstat():
    os.system("sudo apt update")
    os.system("sudo apt install -y darkstat")

# Function to configure darkstat for a specific network interface
def configure_darkstat(interface):
    os.system(f"sudo sed -i 's/START_DARKSTAT=no/START_DARKSTAT=yes/' /etc/darkstat/init.cfg")
    os.system(f"sudo sed -i 's/INTERFACE=\"-i eth0\"/INTERFACE=\"-i {interface}\"/' /etc/darkstat/init.cfg")
    os.system("sudo systemctl restart darkstat")

# Main function where execution of script starts
def main():
    # Extract and save peer connections
    extract_and_save_peer_connections()
    # Read the saved IP data from JSON file
    ip_data = read_json_file('ip.json')

    # Prompt user for speed limit and latency input
    speed = input("Enter the speed limit (in kbit): ")
    latency = input("Enter the latency (in ms): ")

    # Check and prepare network environment
    if not is_module_loaded('ifb') or not is_interface_present('ifb0'):
        print("Failed to prepare network environment. Exiting.")
        return

    # Set up network environment for throttling
    setup_environment(speed, latency)

    # Apply throttling based on user input
    proceed = input("Do you want to apply throttling to all IPs and ports? (yes/no): ").lower()
    if proceed == "yes":
        for item in ip_data:
            apply_throttling(item["ip"], item["port"], speed)

    # Check if darkstat is installed and handle accordingly
    if not is_darkstat_installed():
        choice = input("Do you want to install darkstat for Speed analysis? (yes/no): ").lower()
        if choice == "yes":
            connection_type = input("Are you using a Wi-Fi (wifi) or Ethernet (eth) connection? (wifi/eth): ").lower()
            interface = "wlan0" if connection_type == "wifi" else "eth0"
            install_darkstat()
            configure_darkstat(interface)
            system_ip = os.popen("hostname -I | awk '{print $1}'").read().strip()
            print(f"Access darkstat webpage at: http://{system_ip}:667")
        else:
            print("darkstat installation skipped.")
    else:
        system_ip = os.popen("hostname -I | awk '{print $1}'").read().strip()
        print(f"Darkstat is already installed for Speed analysis, so checkout at: http://{system_ip}:667")

    # Clear throttling settings based on user input
    clear = input("Do you want to clear throttling? (yes/no): ").lower()
    if clear == "yes":
        clear_throttling()

if __name__ == "__main__":
    main()  # Execute main function


