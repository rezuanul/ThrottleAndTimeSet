from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)
INTERFACE = 'wlan0'

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

def set_network_throttle(download_limit="2000kbit", upload_limit="2000kbit"):
    command = f'sudo tc qdisc add dev {INTERFACE} root handle 1: htb default 12 && sudo tc class add dev {INTERFACE} parent 1:1 classid 1:12 htb rate {download_limit} ceil {upload_limit}'
    return execute_command(command)

def reset_network_throttle():
    return execute_command(f'sudo tc qdisc del dev {INTERFACE} root')

def set_time_on_pi(date_time):
    return execute_command(f'sudo date -s "{date_time}"')

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_throttle', methods=['POST'])
def set_throttle_route():
    download_limit = request.json.get('downloadLimit', "2000kbit")
    upload_limit = request.json.get('uploadLimit', "2000kbit")
    success, message = set_network_throttle(download_limit, upload_limit)
    if success:
        return jsonify({'message': 'Throttle set successfully!'})
    else:
        return jsonify({'message': f"Error: {message}"}), 500

@app.route('/clear_throttle', methods=['POST'])
def clear_throttle_route():
    success, message = reset_network_throttle()
    return jsonify({'message': 'Throttle cleared successfully!' if success else f"Error: {message}"}), (200 if success else 500)

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

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
