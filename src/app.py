from flask import Flask, request
from models import db, Telegramuser, TelegramUserVote, Vote
import requests
import locale
from telegram import Telegram
 
app= Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

db.init_app(app)
locale.setlocale(locale.LC_ALL, "German")

@app.before_first_request
def before_first_request_func():
    db.create_all()

@app.route('/api/telegram', methods=['POST'])
def telegram():
    telegram = Telegram()
    telegram.parseUpdate(request.json)
    return ""

    
if __name__ == '__main__':
    print(app.config)
    data = {
        "url": app.config['WEBHOOKURL'],
        }
    response = requests.post(app.config['SETWEBHOOKURL'], data=data)    
    app.run(debug=True)