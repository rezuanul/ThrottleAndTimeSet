import json  # Import the JSON module to work with JSON files
import os  # Import the OS module for interacting with the operating system
import subprocess  # Import the subprocess module for running system commands

def is_module_loaded(module_name):
    # Run 'lsmod' to list all currently loaded modules and capture its output
    result = subprocess.run(['lsmod'], capture_output=True, text=True)
    # Check if the specified module is in the output
    if module_name in result.stdout:
        return True  # Module is already loaded

    # Try to load the module using 'modprobe' if not already loaded
    try:
        subprocess.run(['sudo', 'modprobe', module_name], check=True)
        return True  # Module loading attempted successfully
    except subprocess.CalledProcessError:
        # Handle errors during module loading process
        print(f"Failed to load module {module_name}")
        return False  # Return False if module loading failed

def is_interface_present(interface_name):
    # Check if the specified network interface exists using 'ip link show'
    result = subprocess.run(['ip', 'link', 'show', interface_name], capture_output=True)
    # Evaluate the result of the command
    if result.returncode == 0:
        return True  # Interface exists

    # If interface does not exist, try to add it
    try:
        subprocess.run(['sudo', 'ip', 'link', 'add', 'name', interface_name, 'type', 'ifb'], check=True)
        return True  # Interface creation attempted successfully
    except subprocess.CalledProcessError:
        # Handle errors during interface creation process
        print(f"Failed to add interface {interface_name}")
        return False  # Return False if interface creation failed

# Function to read and return the content of a JSON file
def read_json_file(filename):
    # Open the file in read mode
    with open(filename, 'r') as file:
        # Load and return the JSON content from the file
        return json.load(file)

# Function to set up network traffic control environment
def setup_environment(speed):
    # Add ingress queueing discipline to wlan0 interface
    os.system("sudo tc qdisc add dev wlan0 handle ffff: ingress")
    # Add filter to wlan0 to redirect IP traffic to intermediate functional block (ifb) device
    os.system("sudo tc filter add dev wlan0 parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0")
    # Add hierarchical token bucket (HTB) queueing discipline to ifb0
    os.system("sudo tc qdisc add dev ifb0 root handle 1: htb default 30")
    # Add HTB class to ifb0 with specified rate limit
    os.system(f"sudo tc class add dev ifb0 parent 1: classid 1:1 htb rate {speed}kbit")
    # Add another HTB class to ifb0 for specific traffic control
    os.system(f"sudo tc class add dev ifb0 parent 1:1 classid 1:10 htb rate {speed}kbit")

# Function to apply throttling to specific IP and port
def apply_throttling(ip, port, speed):
    # Add filter to ifb0 for matching specified port and redirecting traffic to a specific class with speed limit
    os.system(f"sudo tc filter add dev ifb0 protocol ip parent 1: prio 1 u32 match ip dport {port} 0xffff flowid 1:10")

# Function to clear all traffic control settings
def clear_throttling():
    # Remove ingress queueing discipline from wlan0
    os.system("sudo tc qdisc del dev wlan0 handle ffff: ingress")
    # Remove queueing discipline from ifb0
    os.system("sudo tc qdisc del dev ifb0 root")

# Function to check if darkstat is installed
def is_darkstat_installed():
    # Execute 'which darkstat' to check if darkstat is in the system's path
    return subprocess.run(['which', 'darkstat'], stdout=subprocess.DEVNULL).returncode == 0

# Function to install darkstat
def install_darkstat():
    # Update the package list
    os.system("sudo apt update")
    # Install darkstat
    os.system("sudo apt install -y darkstat")

# Function to configure darkstat for a specific interface
def configure_darkstat(interface):
    # Modify darkstat config to enable it
    os.system(f"sudo sed -i 's/START_DARKSTAT=no/START_DARKSTAT=yes/' /etc/darkstat/init.cfg")
    # Set the interface for darkstat monitoring
    os.system(f"sudo sed -i 's/INTERFACE=\"-i eth0\"/INTERFACE=\"-i {interface}\"/' /etc/darkstat/init.cfg")

# Main function where execution starts
def main():
    # Read IP data from a JSON file
    ip_data = read_json_file('ip.json')

    # Prompt user for speed limit input
    speed = input("Enter the speed limit (in kbit): ")
	
    # Ensure the 'ifb' module is loaded and 'ifb0' interface is present
    if not is_module_loaded('ifb') or not is_interface_present('ifb0'):
        print("Failed to prepare network environment. Exiting.")
        return

    # Set up network environment for throttling
    setup_environment(speed)

    # Ask user if they want to apply throttling to all IPs and ports
    proceed = input("Do you want to apply throttling to all IPs and ports? (yes/no): ").lower()
    # Apply throttling if user confirms
    if proceed == "yes":
        for item in ip_data:
            # Extract IP and port from the item
            ip = item["ip"]
            port = item["port"]
            # Apply throttling to the extracted IP and port
            apply_throttling(ip, port, speed)

    # Check if darkstat is already installed
    if not is_darkstat_installed():
        # Ask user if they want to install darkstat
        choice = input("Do you want to install darkstat for Speed analysis? (yes/no): ").lower()
        # Install and configure darkstat if user agrees
        if choice == "yes":
            install_darkstat()
            # Ask user for the type of network connection
            connection_type = input("Are you using a Wi-Fi (wifi) or Ethernet (eth) connection? (wifi/eth): ").lower()
            # Choose the appropriate interface based on connection type
            interface = "wlan0" if connection_type == "wifi" else "eth0"
            configure_darkstat(interface)
            # Restart darkstat to apply changes
            os.system("sudo systemctl restart darkstat")
            # Get the system IP address to access darkstat
            system_ip = os.popen("hostname -I | awk '{print $1}'").read().strip()
            print(f"Access darkstat webpage at: http://{system_ip}:667")
        else:
            print("darkstat installation skipped.")
    else:
        # If darkstat is already installed, just print the access URL
        system_ip = os.popen("hostname -I | awk '{print $1}'").read().strip()
        print(f"Darkstat is already installed for Speed analysis, so checkout at: http://{system_ip}:667")

    # Ask user if they want to clear throttling settings
    clear = input("Do you want to clear throttling? (yes/no): ").lower()
    # Clear throttling if user agrees
    if clear == "yes":
        clear_throttling()

# Check if the script is run directly and not imported
if __name__ == "__main__":
    main()  # Execute main function
