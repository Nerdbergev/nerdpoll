import requests
import json
from string import Template
from datetime import datetime
import locale
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship


prefix = 'https://api.telegram.org/bot'
key = '1352429507:AAEQDqrf8C8Tw5XlGgm9OWTvvb_3wrAhbwU'
#chatid = '-1001169425761'

geturl = prefix + key + '/getUpdates'
sendurl = prefix + key + '/sendMessage'
editurl = prefix + key + '/editMessageText'
timeout = 60

text = 'Hast du heute \($day\) vor in den Nerdberg zu kommen?'
options = (
    "Ja, den ganzen Abend",
    "Ja ab 21 Uhr",
    "Ja aber nur vor 21 Uhr",
    "Ja aber nur wenn es nicht so voll ist",
    "Nein"
)
locale.setlocale(locale.LC_ALL, "German")
Base = declarative_base()



class Telegramuser(Base):
    __tablename__ = "telegram"
    id = Column(Integer, primary_key=True)
    telegramid = Column(String)
    name = Column(String)
    
class Vote(Base):
    __tablename__ = "vote"
    id = Column(Integer, primary_key=True)
    telegramid = Column(Integer)
    chat = Column(String)
    
class TelegramUserVote(Base):
   __tablename__ = 'uservote'
   telegramuser_id = Column(Integer, ForeignKey("telegram.id"), primary_key=True)
   vote_id = Column(Integer, ForeignKey("vote.id"), primary_key=True)
   voting = Column(Integer)
   telegramuser = relationship(Telegramuser)
   vote = relationship(Vote)

def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance
    
    
def generateKeyboard():
    array = []
    for id, option in enumerate(options):
        array.append([{
            "text": option,
            "callback_data": id
        }])
    return json.dumps({
        "inline_keyboard": array
    })


def sendPoll(chat):
    data = {
        "chat_id": chat,
        "text": Template(text).substitute(day=datetime.now().strftime("%A")),
        "parse_mode": "MarkdownV2",
        "reply_markup": generateKeyboard()
        }
    response = requests.post(sendurl, data=data)
    return response.json()["result"]["message_id"]

    
    
def sendEditMessage(chatid, messageid, newtext):
    data = {
        "chat_id": chatid,
        "text": newtext,
        "message_id": messageid,
        "parse_mode": "MarkdownV2",
        "reply_markup": generateKeyboard()
        }
    r = requests.post(editurl, data=data)
    
def editMessage(chatid, messageid):
    vote = session.query(Vote).filter(Vote.chat == chatid, Vote.telegramid==messageid).first()
    votings = session.query(TelegramUserVote).join(Telegramuser). \
        filter(TelegramUserVote.vote_id==vote.id).order_by(TelegramUserVote.voting)
    oldid = None
    string = ""
    for vote in votings:
        if oldid != vote.voting:
            string += "\r\n*"+options[vote.voting]+"*:\r\n"
            oldid = vote.voting
        string += "\u2022 @"+vote.telegramuser.name+"\r\n"
    
    sendEditMessage(chatid, messageid, Template(text).substitute(day=datetime.now().strftime("%A"))+"\r\n"+string)
    
def saveUser(user):
    dbuser = session.query(Telegramuser).filter(Telegramuser.telegramid == user['id'])
    if dbuser.count() == 0:
        username = user['username'] if 'username' in user else user['first_name']
        dbuser = Telegramuser(telegramid=user['id'], name=username)
        session.add(dbuser)
        session.commit()
        session.refresh(dbuser)
        return dbuser
    else:
        return dbuser.first()


def saveVote(chat, id):
    session.add(Vote(telegramid=id, chat=chat))
    session.commit()


def updateVoting(user, chatid, vote, voting):
    dbvote = get_or_create(session, Vote, telegramid=vote, chat=chatid )    
    dbvoting = get_or_create(session, TelegramUserVote, telegramuser_id=user.id, vote_id=dbvote.id)
    if dbvoting.voting == voting: 
        return False
    else:
        dbvoting.voting = voting
        session.commit()
        return True


def parseUpdate(update):
    if 'message' in update and 'text' in update['message']:
        if update['message']['text'][0:8].lower() == "/newvote":
            id = sendPoll(update['message']['chat']['id'])
            saveVote(update['message']['chat']['id'], id)            
    elif 'callback_query' in update:
        cbfrom = update['callback_query']['from']
        chatid = update['callback_query']['message']['chat']['id']
        messageid = update['callback_query']['message']['message_id']
        data = update['callback_query']['data']
        
        user= saveUser(cbfrom)
        updateVoting(user, chatid, messageid, data)
        editMessage(chatid, messageid)


def main():

    offset = 0    
    while True:
        dt = dict(offset=offset, timeout=timeout)
        try:
            j = requests.post(geturl, data=dt, timeout=50).json()
        except ValueError:  # incomplete data
            continue
        except requests.ReadTimeout:
            continue
        if not j['ok'] or not j['result']:
            continue
        for r in j['result']:            
            offset = r['update_id'] + 1
            parseUpdate(r)

if __name__ == '__main__':
    try:
        engine = create_engine("sqlite:///database.db", echo=True)
        Session = sessionmaker(bind=engine)
        session = Session()
        Base.metadata.create_all(engine)
        main()
        
    except KeyboardInterrupt:
        exit()