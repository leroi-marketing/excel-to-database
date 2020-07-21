from app import app
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user
from app.models.acl import User
from app.view_models.acl import LoginForm
from werkzeug.urls import url_parse
import click
import getpass
import os


@app.route('/login', methods=['GET', 'POST'])
def login():
    redirect_url = request.args.get('next')
    if not redirect_url or url_parse(redirect_url).netloc != '':
        redirect_url = request.url_root
    if current_user.is_authenticated:
        return redirect(redirect_url)
    form = LoginForm()
    if form.validate_on_submit():
        flash(f'Login requested for user {form.username.data}, remember_me={form.remember_me.data}')
        #user = User.query.filter_by(username=form.username.data).first()
        user = User.get(username=form.username.data)
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember = form.remember_me.data)
        return redirect(redirect_url)
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(request.url_root)

@click.command('generate_pw_hash', short_help="Generates new password hash.")
def generate_pw_hash():
    pw = getpass.getpass("Enter password:")
    salt = input("Enter password salt:")
    print("\nThis is the password hash. Copy it and paste it in auth/auth.json.\n")
    print(User.get_user_password_hash(salt, pw))
