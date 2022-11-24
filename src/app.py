from flask import Flask, request, render_template, redirect, url_for, Response
from models import db, TelegramUserVote, Vote, Webuser, WebUserVote, get_or_create
from sqlalchemy import desc
import queue
import requests
import locale
from telegram import Telegram
from door import is_door_open, is_door_changed 
from flask_apscheduler import APScheduler
from message import MessageAnnouncer

 
app= Flask(__name__, instance_relative_config=True)


app.config.from_pyfile('config.py')


scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
announcer = MessageAnnouncer()
telegram = Telegram(announcer=announcer)


db.init_app(app)
locale.setlocale(locale.LC_ALL, "de_DE.utf-8")

@app.before_first_request
def before_first_request_func():
    data = {
        "url": app.config['WEBHOOKURL'],
        }
    response = requests.post(app.config['SETWEBHOOKURL'], data=data)    
    db.create_all()
    
@scheduler.task('cron', id='do_job_2', minute='*')
def updateDoorState():
    with scheduler.app.app_context():        
        if is_door_changed(scheduler.app):
            dbvote = db.session.query(Vote).filter(Vote.pinned==True)
            for vote in dbvote:
                telegram.editMessage(vote.chat, vote.telegramid, app=scheduler.app)
        
        
@app.route('/api/telegram', methods=['POST'])
def telegramEndpoint():
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
        
    return render_template("overview.html", pollid=dbvote.id, question=dbvote.question, options=options, username=username, avatar=avatar, door_open=is_door_open(app))


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
    telegram.editMessage(vote.chat, vote.telegramid)
    announcer.announce("newVote")
    return redirect(url_for('index'))

@app.route('/api/newvote/<chat>')
def newvote(chat):
    from string import Template
    from datetime import datetime
    text = Template(app.config['TEXT']).substitute(day=datetime.now().strftime("%A"))
    id = telegram.sendPoll(chat, text)
    telegram.saveVote(chat, id, text)
    telegram.pinMessageAndUnpinRecent(chat, id)  
    announcer.announce("newPoll")
    return {'state': True}
   
@app.route('/listen', methods=['GET'])
def listen():

    def stream():
        messages = announcer.listen()  # returns a queue.Queue
        while announcer.has_active_listener(messages):
            try:
                msg = messages.get()  # blocks until a new message arrives
                yield msg
            except queue.Empty:
                # this queue ran full and was removed
                # so we need to disconnect this session to let the
                # client autoreconnect
                pass

    return Response(stream(), mimetype='text/event-stream')         
        
    
if __name__ == '__main__':
    
    app.run(debug=True)
