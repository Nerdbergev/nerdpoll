from string import Template
from flask import current_app as app
from models import Telegramuser, TelegramUserVote, Vote, get_or_create, db, Webuser, WebUserVote
from datetime import datetime
import requests
import json
import shutil
from door import is_door_open


class Telegram():
    def __init__(self, announcer):
        self.announcer = announcer
    
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


    def sendPoll(self, chat, question):
        data = {
            "chat_id": chat,
            "text": question+"\r\n"+self.getDoorMessage(is_door_open(app)),
            "parse_mode": "HTML",
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
    
    def getAvatar(self, user):
        data = {
            "user_id": user.telegramid
            }        
        response = requests.post(app.config['AVATARURL'], data=data).json()
        photos = response['result']['photos']
        if len(photos):
            file_id = photos[0][0]['file_id']
            filename = self.getFiles(file_id)
            extension = filename.split(".")[-1]
            response = requests.get(app.config['FILEPREFIX']+filename, stream=True)
            with open(app.config['UPLOAD_PATH'] + '/' + str(user.telegramid) + '.' + extension, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
                user.icon = str(user.telegramid) + '.' + extension
                db.session.commit()
            del response        
        
    def sendEditMessage(self, chatid, messageid, newtext):
        data = {
            "chat_id": chatid,
            "text": newtext,
            "message_id": messageid,
            "parse_mode": "HTML",
            "reply_markup": self.generateKeyboard()
            }
        r = requests.post(app.config['EDITURL'], data=data)
        
    def editMessage(self, chatid, messageid, app=app):
        poll = db.session.query(Vote).filter(Vote.chat == chatid, Vote.telegramid==messageid).first()
        if not poll:
            print(f"Error, no Vote found with chatid: {chatid}, messageid: {messageid}")
            return False

        votingsTelegram = db.session.query(TelegramUserVote).join(Telegramuser). \
            filter(TelegramUserVote.vote_id==poll.id).order_by(TelegramUserVote.voting)
        votingsWeb = db.session.query(WebUserVote).join(Webuser). \
            filter(WebUserVote.vote_id==poll.id).order_by(WebUserVote.voting)            
        string = ""
        
        options = {i: {"text": txt} for i,txt in enumerate(app.config['OPTIONS'])}
        for option in options:
            options[option]['voters'] = []
            
        for vote in votingsTelegram:
            options[vote.voting]['voters'].append(vote.telegramuser)
        for vote in votingsWeb:
            options[vote.voting]['voters'].append(vote.webuser)                
        
        for oid,oitem in options.items():
            if len(oitem['voters']):
                string += "\r\n<b>"+app.config['OPTIONS'][oid]+"</b>: ("+str(len(oitem['voters']))+" Entitäten)\r\n"
                for votes in oitem['voters']:
                    if isinstance(votes, Telegramuser):
                        string += f"\u2022 <a href=\"tg://user?id={votes.telegramid}\">"                
                        string += votes.username if votes.username else votes.name
                        string += f"</a>\r\n"
                    else:
                        string += "\u2022 "+votes.name+"\r\n"
                        
        string += "\r\n"+self.getDoorMessage(is_door_open(app))
        
        self.sendEditMessage(chatid, messageid, poll.question+"\r\n"+string if poll.question else string)
        
    def saveUser(self, user):
        dbuser = db.session.query(Telegramuser).filter(Telegramuser.telegramid == user['id'])
        if dbuser.count() == 0:
            username = user['username'] if 'username' in user else None
            name = user['first_name'] if 'first_name' in user else None
            dbuser = Telegramuser(telegramid=user['id'], username=username, name=name)
            db.session.add(dbuser)
            db.session.commit()
            db.session.refresh(dbuser)
            return dbuser
        else:
            return dbuser.first()

    def getDoorMessage(self, door):
        from door import is_door_open
        if door:
            return f"\r\nDie Tür ist aktuell <b>offen</b>."
        else:
            return f"\r\nDie Tür ist aktuell <b>geschlossen</b>."
            

    def saveVote(self, chat, id, text):
        db.session.add(Vote(telegramid=id, chat=chat, question=text))
        db.session.commit()
        
    def pinMessage(self, chatid, messageid):
        data = {
            "chat_id": chatid,
            "message_id": messageid,
            "disable_notification": True,
            }
        r = requests.post(app.config['PINMESSAGE'], data=data)
    
    def unpinMessage(self, chatid, messageid):
        data = {
            "chat_id": chatid,
            "message_id": messageid,
            }
        r = requests.post(app.config['UNPINMESSAGE'], data=data)
    
    def pinMessageAndUnpinRecent(self, chat, id):
        dbvote = db.session.query(Vote).filter(Vote.chat == chat, Vote.pinned==True)
        for vote in dbvote:
            vote.pinned = False
            self.unpinMessage(vote.chat, vote.telegramid)        
        
        newvote = db.session.query(Vote).filter(Vote.chat == chat, Vote.telegramid==id).first()
        newvote.pinned = True
        db.session.commit()
        self.pinMessage(newvote.chat, newvote.telegramid)

    def updateVoting(self, user, chatid, vote, voting):
        dbvote = db.session.query(Vote).filter(Vote.telegramid==vote, Vote.chat==chatid ).first()
        if not bool(dbvote):
            return False
        dbvoting = get_or_create(db.session, TelegramUserVote, telegramuser_id=user.id, vote_id=dbvote.id)
        if dbvoting.voting == voting: 
            return False
        else:
            dbvoting.voting = voting
            db.session.commit()
            self.announcer.announce(self.announcer.format_sse(vote, "newvote"))
            return True


    def parseUpdate(self, update):
        if 'message' in update and 'text' in update['message']:
            if update['message']['text'][0:8].lower() == "/newvote":
                text = Template(app.config['TEXT']).substitute(day=datetime.now().strftime("%A"))
                id = self.sendPoll(update['message']['chat']['id'], text)
                self.saveVote(update['message']['chat']['id'], id, text)            
        elif 'callback_query' in update:
            cbfrom = update['callback_query']['from']
            chatid = update['callback_query']['message']['chat']['id']
            messageid = update['callback_query']['message']['message_id']
            data = update['callback_query']['data']
            
            user= self.saveUser(cbfrom)
            self.updateVoting(user, chatid, messageid, data)
            self.editMessage(chatid, messageid)
            self.getAvatar(user)
