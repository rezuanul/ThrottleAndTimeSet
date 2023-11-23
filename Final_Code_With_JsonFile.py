import json
import os

def read_json_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)

def setup_environment(speed):
    #os.system("sudo tc qdisc del dev wlan0 handle ffff: ingress")
    os.system("sudo tc qdisc add dev wlan0 handle ffff: ingress")
    os.system("sudo tc filter add dev wlan0 parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0")
    os.system("sudo tc qdisc add dev ifb0 root handle 1: htb default 30")
    os.system(f"sudo tc class add dev ifb0 parent 1: classid 1:1 htb rate {speed}mbit")
    os.system(f"sudo tc class add dev ifb0 parent 1:1 classid 1:10 htb rate {speed}mbit")

def apply_throttling(ip, port, speed):
    os.system(f"sudo tc filter add dev ifb0 protocol ip parent 1: prio 1 u32 match ip dport {port} 0xffff flowid 1:10")

def clear_throttling():
    os.system("sudo tc qdisc del dev wlan0 handle ffff: ingress")
    os.system("sudo tc qdisc del dev ifb0 root")

def main():
    ip_data = read_json_file('ip.json')

    # Get speed input from user
    speed = input("Enter the speed limit (in mbit): ")

    setup_environment(speed)

    proceed = input("Do you want to apply throttling to all IPs and ports? (yes/no): ").lower()
    if proceed == "yes":
        for item in ip_data:
            ip = item["ip"]
            port = item["port"]
            apply_throttling(ip, port, speed)

    clear = input("Do you want to clear throttling? (yes/no): ").lower()
    if clear == "yes":
        clear_throttling()

if __name__ == "__main__":
    main()
