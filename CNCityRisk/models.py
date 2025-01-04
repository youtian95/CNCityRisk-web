from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# from CNCityRisk import db

# 中国的省份
Province_City_District = {
    '湖北': {
        '武汉': ['武昌'],
    },
    '北京': {
        '北京': ['朝阳', '海淀'],
    },
}


# class User(db.Model, UserMixin):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(20))
#     username = db.Column(db.String(20))
#     password_hash = db.Column(db.String(128))

#     def set_password(self, password):
#         self.password_hash = generate_password_hash(password)

#     def validate_password(self, password):
#         return check_password_hash(self.password_hash, password)


# class Movie(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(60))
#     year = db.Column(db.String(4))
