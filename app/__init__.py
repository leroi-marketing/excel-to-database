from flask import Flask
from config_local import Config
from flask_login import LoginManager


app = Flask(__name__)
app.config.from_object(Config)

login = LoginManager(app)
login.login_view='login'

from app import controllers, models, view_models

app.cli.add_command(controllers.acl.generate_pw_hash)
