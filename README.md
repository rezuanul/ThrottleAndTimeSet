First need to save FinalThrottle2811.py and ip.json file together in the same folder to all raspberry pis.

Then need to run  {sudo python3 FinalThrottle2811.py }.
![image](https://github.com/rezuanul/ThrottleAndTimeSet/assets/45296940/359a076a-f50c-41e1-986b-ac901a38902f)

Everytime you need to clear throattling speed by pressing YES. Otherwise you need to clear the throattling manually for better performance of this system by this commands. 
  {sudo tc qdisc del dev wlan0 handle ffff: ingress}
  {sudo tc qdisc del dev ifb0 root }
  
![image](https://github.com/rezuanul/ThrottleAndTimeSet/assets/45296940/8087cdca-e337-49a1-915d-745eac5f878b)

N.B: All commands need to input without second brackets. 

