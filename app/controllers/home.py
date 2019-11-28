from app import app
from flask import render_template, flash, redirect, url_for, request, json
from flask_login import login_required, current_user
from app.data import sqlify, array2d_to_csv, destination_azuredw, destination_local, destination_redshift
from app.models.acl import User
from config_local import Config
import io


@app.route('/')
@login_required
def index():
    return render_template('upload.html', title='Upload')


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    try:
        # read data as json
        form_data = json.loads(request.data.decode('utf-8'))
        response_texts = []
        # write json data to csv
        for sheet, sheet_data in form_data.items():
            csv = array2d_to_csv(sheet_data)
            table_name = sqlify(sheet)
            if Config.DESTINATION == 'redshift':
                response_texts.append(destination_redshift(csv, table_name, current_user.path))
            elif Config.DESTINATION == 'azuredw':
                response_texts.append(destination_azuredw(csv, table_name, current_user.path))
            else:
                response_texts.append(destination_local(csv, table_name, current_user.path))
        response = app.response_class(
            response=json.dumps(response_texts),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        # return any error as a response to the excel macro
        response = app.response_class(
            response=json.dumps({"error": str(e)}),
            status=500,
            mimetype='application/json'
        )
    return response


@app.route('/submit', methods=['POST'])
def submit():
    """Legacy submit endpoint, that processes authentication based only on a single user password (token)
    """
    try:
        # read data as json
        data = json.loads(request.data.decode('utf-8'))

        # check for presence of all required fields
        for key in ['token', 'name', 'columns', 'data']:
            if key not in data.keys():
                return app.response_class(
                    response=f'Missing data field: {key}\n',
                    status=400,
                    mimetype='text/plain'
                )

        user = User.get('legacy')
        if not user.check_password(data['token']):
            return app.response_class(
                response=f'Invalid token\n',
                status=401,
                mimetype='text/plain'
            )

        # write json data to csv
        tsv_data = io.StringIO(data['data'])
        table_name = sqlify(data['name'])
        if auth.destination == "redshift":
            response_text = destination_redshift(tsv_data, table_name)
        elif auth.destination == 'azuredw':
            response_text = destination_azuredw(tsv_data, table_name)
        else:
            response_text = destination_local(tsv_data, table_name)

        return app.response_class(
            response=response_text,
            status=200,
            mimetype='text/plain'
        )
    except Exception as e:
        # return any error as a response to the excel macro
        return app.response_class(
            response=str(e),
            status=500,
            mimetype='text/plain'
        )
