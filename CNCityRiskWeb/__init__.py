import os
import sys
import warnings

from flask import Flask
from flask_compress import Compress
# from flask_sqlalchemy import SQLAlchemy
# from flask_login import LoginManager

# 仅忽略 cnmaps.maps 中已知的 GeoDataFrame geometry FutureWarning
warnings.filterwarnings(
    action='ignore',
    category=FutureWarning,
    message=r".*adding a column named 'geometry'.*",
    module=r'cnmaps\.maps'
)

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
from CNCityRiskWeb.checks import check_data_integrity

# 启动时检查数据完整性
check_data_integrity(app)
