"""Entry point for application"""

import flask
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import data.constants as const

app = flask.Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{const.DB_LOC}'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = False  # disable expire_on_commit
app.config['WTF_CSRF_ENABLED'] = False # disable CSRF protection
db = SQLAlchemy(app)
app.secret_key = 'dev' # default value during development
socketio = SocketIO(app)
Bootstrap().init_app(app)

# if __name__ == "__main__":
#     URL = "http://127.0.0.1:5000/"
#     webbrowser.open(URL)
#     socketio.run(app, debug=True)
