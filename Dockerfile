FROM python:3.8-slim

RUN apt-get update && \
    apt-get -y install gnupg curl git gcc libffi-dev && \
    curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - && \
    echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN apt-get update && apt-get -y install yarn

RUN mkdir /excel-to-database
WORKDIR /excel-to-database
COPY config.py config_local.py .yarnrc package.json requirements.txt gunicorn.conf.py VBA auth ./
COPY ./app app

RUN pip install -r requirements.txt

RUN yarn install
RUN rm -rf app/static/.auto && mkdir -p app/static/.auto && \
    ln -s /excel-to-database/app/static/resources/@coreui/coreui-free-bootstrap-admin-template/src/css app/static/.auto/css && \
    ln -s /excel-to-database/app/static/resources/@coreui/coreui-free-bootstrap-admin-template/src/img app/static/.auto/img && \
    ln -s /excel-to-database/app/static/resources/@coreui/coreui-free-bootstrap-admin-template/src/js app/static/.auto/js

ENTRYPOINT ["gunicorn"]
CMD ["-w", "4", "-b", "0:5000", "--forwarded-allow-ips", "*", "app:app"]
