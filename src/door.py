import time
import requests
from flask import current_app as app

last_door_check = 0
last_door_status = None

def is_door_open():
    global last_door_check, last_door_status
    now = time.time()
    if last_door_check + 60 < now:
        request = requests.get(app.config['DOORURL'])
        last_door_status = request.json()["state"]["open"] == True
        last_door_check = now
    print(last_door_status)
    return last_door_status
