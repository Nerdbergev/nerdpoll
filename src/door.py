import time
import requests

last_door_check = 0
last_door_status = None

def is_door_open(app):
    global last_door_check, last_door_status
    now = time.time()
    if last_door_check + 60 < now:
        request = requests.get(app.config['DOORURL'])
        last_door_status = request.json()["state"]["open"] == True
        last_door_check = now
    return last_door_status

def is_door_changed(app):
    global last_door_status
    if last_door_status != is_door_open(app):
        return True
    return False
