from app import app
from flask import render_template, flash, redirect, url_for, request, json
from flask_login import login_required, current_user
from app.data import sqlify, array2d_to_csv, destination_azuredw, destination_local, destination_redshift
from config_local import Config


@app.route('/')
@login_required
def index():
    return render_template('upload.html', title='Upload')


@app.route('/submit', methods=['POST'])
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
