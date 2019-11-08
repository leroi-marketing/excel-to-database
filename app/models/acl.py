from datetime import datetime
from app import login
from hashlib import md5
from random import random
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

@login.user_loader
def load_user(id):
    return User.get(id)

class User(UserMixin):
    @staticmethod
    def get(username):
        with open('auth/auth.json', 'r') as fp:
            retrieved = json.load(fp).get(username, None)
            if retrieved:
                return User(username=username, **retrieved)
            return None

    def __init__(self, username, password_hash, password_salt, path=''):
        self.id = username
        self.username = username
        self.password_salt = password_salt
        self.password_hash = password_hash
        self.path = path

    def set_password(self, password):
        self.password_hash = generate_password_hash(self.password_salt + password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, self.password_salt + password)

    @staticmethod
    def get_user_password_hash(salt, password):
        return generate_password_hash(salt + password)

    def __repr__(self):
        return '<User {}>'.format(self.username)
