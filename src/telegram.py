from string import Template
from flask import current_app as app
from models import Telegramuser, TelegramUserVote, Vote, get_or_create, db
from datetime import datetime
import requests
import json
import shutil


class Telegram():
    def generateKeyboard(self):
        array = []
        for id, option in enumerate(app.config['OPTIONS']):
            array.append([{
                "text": option,
                "callback_data": id
            }])
        return json.dumps({
            "inline_keyboard": array
        })


    def sendPoll(self, chat):
        data = {
            "chat_id": chat,
            "text": Template(app.config['TEXT']).substitute(day=datetime.now().strftime("%A")),
            "parse_mode": "MarkdownV2",
            "reply_markup": self.generateKeyboard()
            }
        response = requests.post(app.config['SENDURL'], data=data)
        return response.json()["result"]["message_id"]
    
    def getFiles(self, file_id):
        data = {
            "file_id": file_id
            }
        response = requests.post(app.config['GETFILE'], data=data).json()
        return response['result']['file_path']
    
    def getAvatar(self, id):
        data = {
            "user_id": id
            }        
        response = requests.post(app.config['AVATARURL'], data=data).json()
        file_id = response['result']['photos'][0][0]['file_id']
        filename = self.getFiles(file_id)
        extension = filename.split(".")[-1]
        response = requests.get(app.config['FILEPREFIX']+filename, stream=True)
        with open('static/avatare/' + str(id) + '.' + extension, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response        
        
    def sendEditMessage(self, chatid, messageid, newtext):
        data = {
            "chat_id": chatid,
            "text": newtext,
            "message_id": messageid,
            "parse_mode": "MarkdownV2",
            "reply_markup": self.generateKeyboard()
            }
        r = requests.post(app.config['EDITURL'], data=data)
        
    def editMessage(self, chatid, messageid):
        vote = db.session.query(Vote).filter(Vote.chat == chatid, Vote.telegramid==messageid).first()
        votings = db.session.query(TelegramUserVote).join(Telegramuser). \
            filter(TelegramUserVote.vote_id==vote.id).order_by(TelegramUserVote.voting)
        oldid = None
        string = ""
        for vote in votings:
            if oldid != vote.voting:
                string += "\r\n*"+app.config['OPTIONS'][vote.voting]+"*:\r\n"
                oldid = vote.voting
            string += "\u2022 @"+vote.telegramuser.name+"\r\n"
        
        self.sendEditMessage(chatid, messageid, Template(app.config['TEXT']).substitute(day=datetime.now().strftime("%A"))+"\r\n"+string)
        
    def saveUser(self, user):
        dbuser = db.session.query(Telegramuser).filter(Telegramuser.telegramid == user['id'])
        if dbuser.count() == 0:
            username = user['username'] if 'username' in user else user['first_name']
            dbuser = Telegramuser(telegramid=user['id'], name=username)
            db.session.add(dbuser)
            db.session.commit()
            db.session.refresh(dbuser)
            return dbuser
        else:
            return dbuser.first()


    def saveVote(self, chat, id):
        db.session.add(Vote(telegramid=id, chat=chat))
        db.session.commit()


    def updateVoting(self, user, chatid, vote, voting):
        dbvote = get_or_create(db.session, Vote, telegramid=vote, chat=chatid )    
        dbvoting = get_or_create(db.session, TelegramUserVote, telegramuser_id=user.id, vote_id=dbvote.id)
        if dbvoting.voting == voting: 
            return False
        else:
            dbvoting.voting = voting
            db.session.commit()
            return True


    def parseUpdate(self, update):
        if 'message' in update and 'text' in update['message']:
            if update['message']['text'][0:8].lower() == "/newvote":
                id = self.sendPoll(update['message']['chat']['id'])
                self.saveVote(update['message']['chat']['id'], id)            
        elif 'callback_query' in update:
            cbfrom = update['callback_query']['from']
            chatid = update['callback_query']['message']['chat']['id']
            messageid = update['callback_query']['message']['message_id']
            data = update['callback_query']['data']
            
            user= self.saveUser(cbfrom)
            self.updateVoting(user, chatid, messageid, data)
            self.editMessage(chatid, messageid)
            self.getAvatar(cbfrom['id'])