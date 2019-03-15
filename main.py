import json
import io
import gzip
from types import SimpleNamespace

import boto3
import pandas as pd
import sqlalchemy
from flask import Flask, request

with open('../auth/auth.json') as f:
    auth = SimpleNamespace(**json.load(f))

s3client = boto3.client('s3', aws_access_key_id=auth.s3['key_id'], aws_secret_access_key=auth.s3['key'])
engine = sqlalchemy.create_engine('redshift://{user}:{password}@{host}:{port}/{dbname}'.format(**auth.db))


def list_to_matrix(l, n):
    # turn list into matrix of n columns
    return [l[i:i + n] for i in range(0, len(l), n)]


def to_alnum(string):
    # get rid of non alpahunmeric characters except underscores
    return ''.join(char for char in string if char.isalnum() or char == '_')


def generate_table_stmt(schema, table, columns):
    # gernerate a create table statement
    alnum_columns = [to_alnum(column) for column in columns]
    cols_type = ','.join(['{} VARCHAR'.format(col) for col in alnum_columns])
    return 'CREATE TABLE {schema}.{table}({cols_type})'.format(**locals())


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
            return 'Missing data field: {key}\n'.format(key=key)

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
        header = data_matrix.pop(0)
        df = pd.DataFrame(data_matrix, columns=header)

        # load to redshift
        table_name = data['name'].lower()
        key = 'excel-to-database/{}.csv.gz'.format(table_name)
        arn = auth.s3['arn']
        bucket = auth.s3['bucket']

        # load to s3 bucket
        s3_copy(bucket, key, df)

        # load to redshift
        copy_stmt = '''COPY x_excel.{table_name}
                    FROM 's3://{bucket}/{key}'
                    iam_role '{arn}'
                    GZIP
                    delimiter ','
                    COMPUPDATE OFF
                    region 'eu-central-1';'''.format(**locals())

        # copy to redshift
        connection = engine.connect()
        connection.execute('DROP TABLE IF EXISTS x_excel.{}'.format(table_name))
        connection.execute(generate_table_stmt('x_excel', table_name, header))
        connection.execute(copy_stmt)
        connection.close()
        return '{} loaded successfully.\n'.format(data['name'])

    except Exception as e:
        # return any error as a response to the excel macro
        return e


if __name__ == '__main__':
    app.run(ssl_context='adhoc',
            host='0.0.0.0',
            port=5000)
