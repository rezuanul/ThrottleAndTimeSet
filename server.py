from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)

# Utility Functions
def execute_command(command):
    """Execute shell command and return its success status."""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"Command failed with exit status: {result.returncode}")
            print(f"Error:\n{result.stderr}")
            return False, result.stderr
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        print(f"Output:\n{e.output}")
        return False, e.output

def enable_ntp():
    return execute_command('sudo timedatectl set-ntp on')

def disable_ntp_and_set_time(date_time):
    success, _ = execute_command('sudo timedatectl set-ntp off')
    if success:
        return set_time_on_pi(date_time)
    return False, "Failed to disable NTP."

def set_time_on_pi(date_time):
    return execute_command(f'sudo date -s "{date_time}"')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup_environment', methods=['POST'])
def setup_environment():
    # First, attempt to delete any existing qdisc that might be attached
    subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "wlan0", "handle", "ffff:", "ingress"], stderr=subprocess.DEVNULL)
    # Add ingress qdisc
    subprocess.run(["sudo", "tc", "qdisc", "add", "dev", "wlan0", "handle", "ffff:", "ingress"], check=True)
    # Redirect all ingress traffic to ifb0
    subprocess.run(["sudo", "tc", "filter", "add", "dev", "wlan0", "parent", "ffff:", "protocol", "ip", "u32", "match", "u32", "0", "0", "action", "mirred", "egress", "redirect", "dev", "ifb0"], check=True)
    return jsonify(message="Environment setup completed")

@app.route('/throttle', methods=['POST'])
def throttle():
    data = request.json
    port = data.get('port')
    speed = data.get('speed')
    speed_str = f"{speed}mbit"

    # Delete any existing qdisc for ifb0
    subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "ifb0", "root"], stderr=subprocess.DEVNULL)
    # Set up HTB qdisc on ifb0
    subprocess.run(["sudo", "tc", "qdisc", "add", "dev", "ifb0", "root", "handle", "1:", "htb", "default", "30"], check=True)
    # Add main class with dynamic rate
    subprocess.run(["sudo", "tc", "class", "add", "dev", "ifb0", "parent", "1:", "classid", "1:1", "htb", "rate", speed_str], check=True)
    # Add specific class for the dynamic port with the same rate
    subprocess.run(["sudo", "tc", "class", "add", "dev", "ifb0", "parent", "1:1", "classid", "1:10", "htb", "rate", speed_str], check=True)
    # Attach filter for the dynamic port
    subprocess.run(["sudo", "tc", "filter", "add", "dev", "ifb0", "protocol", "ip", "parent", "1:", "prio", "1", "u32", "match", "ip", "dport", port, "0xffff", "flowid", "1:10"], check=True)
    return jsonify(message=f"Throttling applied to port {port} at {speed}mbit/s")

@app.route('/clear_throttle', methods=['POST'])
def clear_throttle():
    # Attempt to delete any existing qdisc for wlan0 and ifb0
    subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "wlan0", "handle", "ffff:", "ingress"], stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "ifb0", "root"], stderr=subprocess.DEVNULL)
    return jsonify(message="Throttling cleared")

@app.route('/enable_ntp', methods=['POST'])
def enable_ntp_route():
    success, message = enable_ntp()
    return jsonify({'message': 'NTP enabled successfully!' if success else f"Error: {message}"}), (200 if success else 500)

@app.route('/set_custom_time', methods=['POST'])
def set_custom_time_route():
    date_time = request.json.get('dateTime')
    if date_time:
        success, message = disable_ntp_and_set_time(date_time)
        return jsonify({'message': 'Time set successfully after disabling NTP!' if success else f"Error: {message}"}), (200 if success else 500)
    else:
        return jsonify({'message': "dateTime field is missing in the request."}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
