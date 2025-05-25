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

# 优化压缩配置
app.config['COMPRESS_MIMETYPES'] = [
    'text/html',
    'text/css',
    'text/xml',
    'application/json',
    'application/javascript'
]
app.config['COMPRESS_LEVEL'] = 6  # 压缩级别 1-9
app.config['COMPRESS_MIN_SIZE'] = 50  # 最小压缩大小

compress = Compress(app)


from CNCityRiskWeb import views, errors, commands
