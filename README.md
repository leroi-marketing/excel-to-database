# excel-to-database
Solution to synchronize small tables between Excel and a database

## Setup

#### Install frontend

##### Install `yarn`

```sh
curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
sudo apt update && sudo apt install yarn
```

##### Install frontend dependencies using `yarn`, and link them
```sh
yarn install
rm -rf app/static/.auto
mkdir -p app/static/.auto
ln -s $(pwd)/app/static/resources/@coreui/coreui-free-bootstrap-admin-template/src/css app/static/.auto/css
ln -s $(pwd)/app/static/resources/@coreui/coreui-free-bootstrap-admin-template/src/img app/static/.auto/img
ln -s $(pwd)/app/static/resources/@coreui/coreui-free-bootstrap-admin-template/src/js app/static/.auto/js
```

#### Install dependencies

```sh
# In case it's not yet installed, install virtualenv
sudo apt-get install python3-virtualenv

# Create virtualenv locally
virtualenv -p python3.6 venv

# activate virtualenv
source venv/bin/activate

# Install dependencies
pip install --upgrade -r requirements.txt
```

#### Configure

Configure Flask App in the virtualenv:
```sh
# Add flask app info to venv, and re-activate environment
echo "export FLASK_APP=app/app.py" >> venv/bin/activate
source venv/bin/activate
```

Create `config_local.py` file in this directory, by making a copy of `config_local.py.example` and setting up the parameters.

Create `auth/auth.json` with the contents:
```json
{
    "<username>": {
        "password_hash": "pbkdf2:sha256:50000$GS62LgsS$fd786e13bb85bd4b9c1c71609e103b2a66eebbb751f9b92f7cbc1d195b65f71d",
        "password_salt": "asd",
        "path": "optional/relative-path-for-user-uploaded-files"
    }
}
```
for each user create a new record. The file is read during each authentication, so any update won't require an app restart.

Meaning of each parameter:
* `<username>` is the username used for login
* `password_salt` is a random string. It's not a secret, can almost be public. Preferrably longer than 3 letters.
* `password_hash` is a generated password hash. To generate it for a user, run `flask generate_pw_hash` with virtualenv activated. For this to work, the previous step in "Install dependencies"


#### Run for development:
```sh
# make sure venv is activated
source venv/bin/activate
# Otherwise just run this
flask run --with-threads --reload --eager-loading --host ::0 --port 5000 2>&1
```

#### Run for production
with `gunicorn`
```sh
gunicorn -w 4 -b 0:5000 --forwarded-allow-ips "*" app:app
```

#### Run some more

If it's on Linux that uses systemd for init, create this `excel.service` file:
```ini
[Unit]
Description=Excel database upload endpoint
After=network.target

[Service]
PermissionsStartOnly = true
PIDFile = /run/excel/excel.pid
WorkingDirectory=/path/to/excel-to-database
ExecStartPre = /bin/mkdir /run/excel
ExecStartPre = /bin/chown -R excel:excel /run/excel
# This line enables it to listen only on the loopback interface, which is what is necessary
# if you have a reverse proxy (nginx) on the same machine to handle HTTPS for example
ExecStart=venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app --pid /run/excel/excel.pid
# This line is for the case when it has to listen to all network interfaces
# ExecStart=venv/bin/gunicorn -w 4 -b 0:5000 app:app --pid /run/excel/excel.pid
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s HUP $MAINPID
ExecStopPost=/bin/rm -rf /run/excel 
Restart=on-abort
User=excel
Group=excel
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target

[Unit]
Description=Excel database upload endpoint
After=network.target
```

...if it's on Ubuntu or Debian, this file should be located at `/lib/systemd/system/excel.service`.

Then, make sure you create `excel` user and group.
```sh
sudo useradd excel
```

Once that is done, refresh service list, make sure it's enabled, and started.

```sh
sudo systemctl daemon-reload
sudo systemctl enable excel
sudo systemctl restart excel
```

To check whether the service is running, or whether there are any errors:

```sh
systemctl status excel
```

The service will start automatically
