from flask import Flask, request, render_template, redirect, url_for
from models import db, TelegramUserVote, Vote, Webuser, WebUserVote, get_or_create
from sqlalchemy import desc
import requests
import locale
from telegram import Telegram
 
app= Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

db.init_app(app)
locale.setlocale(locale.LC_ALL, "de_DE.utf-8")

@app.before_first_request
def before_first_request_func():
    db.create_all()

@app.route('/api/telegram', methods=['POST'])
def telegram():
    telegram = Telegram()
    telegram.parseUpdate(request.json)
    return ""

@app.route('/')
def index():
    avatar = request.args.get('avatar', "")
    username = request.args.get('username')
    dbvote = db.session.query(Vote).order_by(desc(Vote.id)).first()
    votesTelegram = db.session.query(TelegramUserVote).filter(TelegramUserVote.vote_id == dbvote.id)
    votesWeb = db.session.query(WebUserVote).filter(WebUserVote.vote_id == dbvote.id)
    options = {i: {"text": txt} for i,txt in enumerate(app.config['OPTIONS'])}
    for option in options:
        options[option]['voters'] = []
        
    for vote in votesTelegram:
        options[vote.voting]['voters'].append(vote.telegramuser)
    for vote in votesWeb:
        options[vote.voting]['voters'].append(vote.webuser)        
        
    return render_template("overview.html", pollid=dbvote.id, question=dbvote.question, options=options, username=username, avatar=avatar)


@app.route('/vote')
def vote():
    if request.args.get('username') in [None, ""]:
        return "Failed - No username"
    if request.args.get('avatar') in [None, ""]:
        return "Failed - No avatar"
    if request.args.get('pollid') in [None, ""]:
        return "Failed - No pollid"
    if request.args.get('voting') in [None, ""]:
        return "Failed - No voting"       
    
    user = get_or_create(db.session, Webuser, name=request.args.get('username'))
    voting = get_or_create(db.session,WebUserVote, webuser_id=user.id, vote_id=request.args.get('pollid'))
    vote = db.session.query(Vote).filter(Vote.id == request.args.get('pollid')).first()
    user.icon = request.args.get('avatar')
    voting.voting = request.args.get('voting')
    db.session.commit()
    telegram = Telegram()
    telegram.editMessage(vote.chat, vote.telegramid)
    return redirect(url_for('index'))

@app.route('newvote')
def newvote(chat):
    from string import Template
    from datetime import datetime
    text = Template(app.config['TEXT']).substitute(day=datetime.now().strftime("%A"))
    id = telegram.sendPoll(chat, text)
    telegram.saveVote(chat, id, text)      
         
        
    
if __name__ == '__main__':
    data = {
        "url": app.config['WEBHOOKURL'],
        }
    response = requests.post(app.config['SETWEBHOOKURL'], data=data)    
    app.run(debug=True)