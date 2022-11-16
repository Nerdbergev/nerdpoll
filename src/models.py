
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()



class Telegramuser(db.Model):
    __tablename__ = "telegram"
    id = db.Column(db.Integer, primary_key=True)
    telegramid = db.Column(db.String)
    name = db.Column(db.String)
    
class Vote(db.Model):
    __tablename__ = "vote"
    id = db.Column(db.Integer, primary_key=True)
    telegramid = db.Column(db.Integer)
    chat = db.Column(db.String)
    
class TelegramUserVote(db.Model):
   __tablename__ = 'uservote'
   telegramuser_id = db.Column(db.Integer, db.ForeignKey("telegram.id"), primary_key=True)
   vote_id = db.Column(db.Integer, db.ForeignKey("vote.id"), primary_key=True)
   voting = db.Column(db.Integer)
   telegramuser = db.relationship(Telegramuser)
   vote = db.relationship(Vote)
      
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