import json
import io
import os
import gzip
from types import SimpleNamespace

import csv
from flask import Flask, request
import re

with open('../auth/auth.json') as f:
    auth = SimpleNamespace(**json.load(f))

if hasattr(auth, 's3'):
    import boto3
    s3client = boto3.client('s3', aws_access_key_id=auth.s3['key_id'], aws_secret_access_key=auth.s3['key'])

def list_to_matrix(l, n):
    # turn list l into 2D matrix of n columns
    return [l[i:i + n] for i in range(0, len(l), n)]


def to_alnum(string):
    # get rid of non alpahunmeric characters except underscores
    return ''.join(char for char in string if char.isalnum() or char == '_')


def generate_table_stmt(schema, table, columns, text_type_name='VARCHAR'):
    # gernerate a create table statement
    alnum_columns = [to_alnum(column) for column in columns]
    cols_type = ','.join([f'{col} {text_type_name}' for col in alnum_columns])
    return f'CREATE TABLE {schema}.{table}({cols_type})'


def s3_copy(bucket: str, key: str, csv_reader):
    # copy a pandas csv_reader as a csv.gz to s3
    def compress(string, cp='utf-8'):
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='w') as f:
            f.write(string.encode(cp))
        return out.getvalue()

    header = next(csv_reader)
    body_io = io.StringIO()
    writer = csv.writer(body_io)
    _ = list(writer.writerow(row) for row in csv_reader)
    body_io.seek(0)
    body = compress(body_io.read())
    s3client.put_object(Bucket=bucket, Key=key, Body=body)


def sqlify(name: str):
    return re.sub(r"[^a-zA-Z0-9]+", "_", name.lower())


def destination_redshift(tsv_data: io.StringIO, table_name: str):
    import sqlalchemy
    from sqlalchemy.sql import text

    dsn = 'redshift://{user}:{password}@{host}:{port}/{dbname}'.format(**auth.db)
    engine = sqlalchemy.create_engine(dsn)

    reader = csv.reader(tsv_data, delimiter='\t')
    key = f'excel-to-database/{table_name}.csv.gz'
    arn = auth.s3['arn']
    bucket = auth.s3['bucket']

    # load to s3 bucket
    s3_copy(bucket, key, reader)

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
    tsv_data.seek(0)
    header = next(reader)
    n_records = len(reader)
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


def destination_local(tsv_data: io.StringIO, table_name: str):
    path = auth.local_dest
    if not os.path.isdir(path):
        os.mkdirs(path)

    filename = f'{path}/{table_name}.csv'
    n_records = 0
    with open(filename, 'w') as fp:
        writer = csv.writer(fp)
        reader = csv.reader(tsv_data, delimiter='\t')
        for row in reader:
            writer.writerow(row)
            n_records += 1

    return f'Created {filename}.\n{n_records-1} records loaded successfully.\n'


def destination_azuredw(tsv_data: io.StringIO, table_name: str):
    import pyodbc

    conn = pyodbc.connect(
        'DRIVER={driver};SERVER=tcp:{host};DATABASE={dbname};UID={user};PWD={password}'.format(
                **auth.db
            )
        )
    conn.autocommit = True
    cursor = conn.cursor()

    reader = csv.reader(tsv_data, delimiter='\t')

    # compare sorted and upper col names as it is tricky to control case and order (not an ideal solution)
    tsv_data.seek(0)
    header = next(reader)

    cursor.execute(f"""
    IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name='x_excel') EXEC('CREATE SCHEMA x_excel')
    """)

    cursor.execute(f"""
    IF EXISTS (SELECT 1
               FROM sys.schemas
               JOIN sys.tables ON schemas.schema_id=tables.schema_id
               WHERE schemas.name='x_excel' AND tables.name='{table_name}')
    DROP TABLE x_excel.{table_name}
    """)
    cursor.execute(generate_table_stmt('x_excel', table_name, header, 'NVARCHAR(2000)'))
    print("Created table")
    inserts = []
    n_records = 0
    for row in reader:
        n_records += 1
        inserts.append(f"INSERT INTO x_excel.{table_name} VALUES (N'" +
                       "', N'".join(map(lambda col: col.replace("'", "''"), row)) +
                       "');\n")
        if len(inserts) == 1000:
            statement = "".join(inserts)
            print("Executing batch")
            cursor.execute(statement)
            inserts = []
    if inserts:
        statement = "".join(inserts)
        print("Executing last batch")
        cursor.execute(statement)

    return f'Loaded into x_excel.{table_name}.\n{n_records} records loaded successfully.\n'


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
        tsv_data = io.StringIO(data['data'])
        table_name = sqlify(data['name'])
        if auth.destination == "redshift":
            return destination_redshift(tsv_data, table_name)
        elif auth.destination == 'azuredw':
            return destination_azuredw(tsv_data, table_name)
        else:
            return destination_local(tsv_data, table_name)

    except Exception as e:
        # return any error as a response to the excel macro
        return e


if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=5000)
