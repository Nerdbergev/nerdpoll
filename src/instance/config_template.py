prefix = 'https://api.telegram.org/bot'
key = ''

GETURL = prefix + key + '/getUpdates'
SENDURL = prefix + key + '/sendMessage'
EDITURL = prefix + key + '/editMessageText'
SETWEBHOOKURL = prefix + key + '/setWebhook'
AVATARURL = prefix + key + '/getUserProfilePhotos'
GETFILE = prefix + key + '/getFile'
FILEPREFIX = 'https://api.telegram.org/file/bot' + key + '/'
WEBHOOKURL = 'https://poll.nerdberg.de/api/telegram'
DOORURL = 'https://status.nerdberg.de/api/doorstatus/'

TEXT = 'Hast du heute \($day\) vor in den Nerdberg zu kommen?'
OPTIONS = (
    "Ja, den ganzen Abend",
    "Ja ab 21 Uhr",
    "Ja aber nur vor 21 Uhr",
    "Vielleicht",
    "Nein"
)
SQLALCHEMY_DATABASE_URI = 'sqlite:///sqlite.db'
UPLOAD_PATH = '/opt/nerdbergbot/src/static/avatare'
