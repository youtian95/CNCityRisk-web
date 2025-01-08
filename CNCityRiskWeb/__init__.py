import os
import sys

from flask import Flask
from flask_compress import Compress
# from flask_sqlalchemy import SQLAlchemy
# from flask_login import LoginManager

# SQLite URI compatible
WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
compress = Compress(app)


from CNCityRiskWeb import views, errors, commands
