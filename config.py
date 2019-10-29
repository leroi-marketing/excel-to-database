import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SESSION_TYPE = 'filesystem'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'not-gonna-guess-it'
