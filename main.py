import json
import io
import gzip
from types import SimpleNamespace

import pandas as pd
import sqlalchemy
from sqlalchemy.sql import text
from flask import Flask, request

with open('../auth/auth.json') as f:
    auth = SimpleNamespace(**json.load(f))

if hasattr(auth, 's3'):
    import boto3
    s3client = boto3.client('s3', aws_access_key_id=auth.s3['key_id'], aws_secret_access_key=auth.s3['key'])

if hasattr(auth, 'db'):
    engine = sqlalchemy.create_engine('redshift://{user}:{password}@{host}:{port}/{dbname}'.format(**auth.db))


def list_to_matrix(l, n):
    # turn list l into 2D matrix of n columns
    return [l[i:i + n] for i in range(0, len(l), n)]


def to_alnum(string):
    # get rid of non alpahunmeric characters except underscores
    return ''.join(char for char in string if char.isalnum() or char == '_')


def generate_table_stmt(schema, table, columns):
    # gernerate a create table statement
    alnum_columns = [to_alnum(column) for column in columns]
    cols_type = ','.join([f'{col} VARCHAR' for col in alnum_columns])
    return f'CREATE TABLE {schema}.{table}({cols_type})'


def s3_copy(bucket, key, dataframe):
    # copy a pandas dataframe as a csv.gz to s3
    def compress(string, cp='utf-8'):
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='w') as f:
            f.write(string.encode(cp))
        return out.getvalue()

    body = compress(dataframe.to_csv(index=False, header=False))
    s3client.put_object(Bucket=bucket, Key=key, Body=body)


app = Flask(__name__)


@app.route('/submit', methods=['POST'])
def post_route():
    # read data as json
    data = request.get_json(force=True)

    # check for presence of all required fields
    for key in ['token', 'name', 'columns', 'data']:
        if key not in data.keys():
            return f'Missing data field: {key}\n'

    # load token
    with open('../auth/auth.json') as f:
        token = json.load(f)['token']

    # check for valid token
    if data['token'] != token:
        return 'Invalid token\n'

    try:
        # write json data to csv
        list_data = data['data'].split('\t')
        data_matrix = list_to_matrix(list_data, data['columns'])
        header = [col_name.upper() for col_name in data_matrix.pop(0)]
        df = pd.DataFrame(data_matrix, columns=header)
        n_records = df.shape[0]

        # load to redshift
        table_name = data['name'].lower()
        key = f'excel-to-database/{table_name}.csv.gz'
        arn = auth.s3['arn']
        bucket = auth.s3['bucket']

        # load to s3 bucket
        s3_copy(bucket, key, df)

        # load to redshift
        copy_stmt = f'''COPY x_excel.{table_name}
                    FROM 's3://{bucket}/{key}'
                    iam_role '{arn}'
                    GZIP
                    csv
                    COMPUPDATE OFF
                    region 'eu-central-1';'''

        # get column names
        connection = engine.connect()
        col_names = connection.execute(f'SELECT COLUMN_NAME from INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=\'{table_name}\'')
        col_names = [col_name.values()[0].upper() for col_name in col_names]

        # compare sorted and upper col names as it is tricky to control case and order (not an ideal solution)
        if sorted(col_names) == sorted(header):
            # truncate if cols seem to be the same (will fail if only column order is changed)
            action = 'Truncated'
            connection.execute(f'Truncate TABLE x_excel.{table_name}')
        else:
            # drop if col names not the same
            action = 'Dropped'
            connection.execute(f'DROP TABLE IF EXISTS x_excel.{table_name} CASCADE')
            connection.execute(generate_table_stmt('x_excel', table_name, header))

        connection.execute(text(copy_stmt).execution_options(autocommit=True))
        return f'{action} and loaded into x_excel.{table_name}.\n{n_records} records loaded successfully.\n'

    except Exception as e:
        # return any error as a response to the excel macro
        return e


if __name__ == '__main__':
    app.run(ssl_context='adhoc',
            host='0.0.0.0',
            port=5000)
