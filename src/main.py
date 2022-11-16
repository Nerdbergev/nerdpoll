from flask import Flask
from models import db, Telegramuser, TelegramUserVote, Vote


app= Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sqlite.db'

db.init_app(app)

if __name__ == '__main__':
    app.run(debug=True)