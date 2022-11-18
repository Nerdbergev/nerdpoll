import time
import requests
from flask import current_app as app

last_door_check = 0
last_door_status = None

def is_door_open():
	now = time.time()
	if last_door_check + 60 < now:
		last_door_status = requests.get(app.config['DOORURL']).json()["results"][0]["status"] == 'open'
		last_door_check = now
	return last_door_status
