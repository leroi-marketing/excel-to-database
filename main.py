import json

import pandas as pd
import sqlalchemy
from flask import Flask, request


def list_to_matrix(l, n):
    # turn list into matrix of n columns
    return [l[i:i + n] for i in range(0, len(l), n)]


def get_engine():
    with open('auth/auth.json') as f:
        db_cred = json.load(f)['db']
    return sqlalchemy.create_engine('redshift://{user}:{password}@{host}:{port}/{dbname}'.format(**db_cred))


app = Flask(__name__)


# add query endpoint
# rename post -> submit
# add schema option json
# ssl
# security token
# protect vba from view tools -> vba project properties ->
# truncate if exists else drop and overwrite
# add info on number of rows columns, schema and table names
# useful error messages
# escape chars
# move to github
# add documentation


@app.route('/post', methods=['POST'])
def post_route():
    # read data as json
    data = request.get_json(force=True)

    # write json data to csv
    list_data = data['data'].split('\t')
    data_matrix = list_to_matrix(list_data, data['columns'])
    header = data_matrix.pop(0)
    df = pd.DataFrame(data_matrix, columns=header)

    # load to redshift
    table_name = data['name'].lower()
    df.to_sql(table_name, get_engine(), schema='x_excel', if_exists='replace', index=False)
    return '{} loaded successfully.\n'.format(data['name'])


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
