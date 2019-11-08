from types import SimpleNamespace
from typing import List
from config_local import Config
import json
import io
import gzip
import re
import csv
import os

if hasattr(Config, 'S3'):
    import boto3
    s3client = boto3.client('s3', aws_access_key_id=Config.S3['key_id'], aws_secret_access_key=Config.S3['key'])


def list_to_matrix(l, n):
    """turn list l into 2D matrix of n columns
    """
    return [l[i:i + n] for i in range(0, len(l), n)]


def to_alnum(string):
    """Get rid of non alpahunmeric characters except underscores
    """
    return ''.join(char for char in string if char.isalnum() or char == '_')


def array2d_to_csv(in_list: List[List[str]]) -> io.StringIO:
    """Converts a list of lists into a csv StringIO object
    """
    result = io.StringIO()
    writer = csv.writer(result).writerows(in_list)
    result.seek(0)
    return result


def generate_table_stmt(schema, table, columns, text_type_name='VARCHAR'):
    """gernerate a create table statement
    """
    alnum_columns = [to_alnum(column) for column in columns]
    cols_type = ','.join([f'{col} {text_type_name}' for col in alnum_columns])
    return f'CREATE TABLE {schema}.{table}({cols_type})'


def s3_copy(bucket: str, key: str, csv_reader):
    """copy a pandas csv_reader as a csv.gz to s3
    """
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


def destination_redshift(csv_data: io.StringIO, table_name: str, path: str):
    import sqlalchemy
    from sqlalchemy.sql import text

    dsn = 'redshift://{user}:{password}@{host}:{port}/{dbname}'.format(**Config.DB)
    engine = sqlalchemy.create_engine(dsn)

    reader = csv.reader(csv_data)
    key = f'excel-to-database/{table_name}.csv.gz'
    arn = Config.S3['arn']
    bucket = Config.S3['bucket']

    # load to s3 bucket
    s3_copy(bucket, key, reader)

    # load to redshift
    schema_name = 'x_excel'
    if path:
        schema_name += '_' + path
    copy_stmt = f'''COPY {schema_name}.{table_name}
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
    csv_data.seek(0)
    header = next(reader)
    n_records = len(reader)
    if sorted(col_names) == sorted(header):
        # truncate if cols seem to be the same (will fail if only column order is changed)
        action = 'Truncated'
        connection.execute(f'Truncate TABLE {schema_name}.{table_name}')
    else:
        # drop if col names not the same
        action = 'Dropped'
        connection.execute(f'DROP TABLE IF EXISTS {schema_name}.{table_name} CASCADE')
        connection.execute(generate_table_stmt(schema_name, table_name, header))

    connection.execute(text(copy_stmt).execution_options(autocommit=True))
    return f'{action} and loaded into {schema_name}.{table_name}.\n{n_records} records loaded successfully.\n'


def destination_local(csv_data: io.StringIO, table_name: str, path: str):
    if path:
        if path[0] != '/':
            path = Config.LOCAL_DEST + '/' + path
    else:
        path = Config.LOCAL_DEST

    if not os.path.isdir(path):
        os.makedirs(path)

    filename = f'{path}/{table_name}.csv'
    n_records = 0
    with open(filename, 'w') as fp:
        writer = csv.writer(fp)
        reader = csv.reader(csv_data)
        for row in reader:
            writer.writerow(row)
            n_records += 1

    return f'Created {filename}.\n{n_records-1} records loaded successfully.\n'


def destination_azuredw(csv_data: io.StringIO, table_name: str, path: str):
    import pyodbc

    conn = pyodbc.connect(
        'DRIVER={driver};SERVER=tcp:{host};DATABASE={dbname};UID={user};PWD={password}'.format(
                **Config.DB
            )
        )
    conn.autocommit = True
    cursor = conn.cursor()

    reader = csv.reader(csv_data)

    # compare sorted and upper col names as it is tricky to control case and order (not an ideal solution)
    csv_data.seek(0)
    header = next(reader)

    schema_name = 'x_excel'
    if path:
        schema_name += '_' + path

    cursor.execute(f"""
    IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name='{schema_name}') EXEC('CREATE SCHEMA {schema_name}')
    """)

    cursor.execute(f"""
    IF EXISTS (SELECT 1
               FROM sys.schemas
               JOIN sys.tables ON schemas.schema_id=tables.schema_id
               WHERE schemas.name='{schema_name}' AND tables.name='{table_name}')
    DROP TABLE {schema_name}.{table_name}
    """)
    cursor.execute(generate_table_stmt(schema_name, table_name, header, 'NVARCHAR(2000)'))

    inserts = []
    n_records = 0
    for row in reader:
        n_records += 1
        inserts.append(f"INSERT INTO {schema_name}.{table_name} VALUES (N'" +
                       "', N'".join(map(lambda col: col.replace("'", "''"), row)) +
                       "');\n")
        if len(inserts) == 1000:
            statement = "".join(inserts)
            cursor.execute(statement)
            inserts = []
    if inserts:
        statement = "".join(inserts)
        cursor.execute(statement)

    return f'Loaded into {schema_name}.{table_name}.\n{n_records} records loaded successfully.\n'
