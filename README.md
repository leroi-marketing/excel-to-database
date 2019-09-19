# excel-to-database
Solution to synchronize small tables between Excel and a database

## Setup

Create `../auth/auth.json` file (relative to `main.py`) with this content (sample):

### Azure Data Warehouse
```json
{
    "token": "123asd",
    "destination": "azuredw",
    "db": {
        "user": "dbuser",
        "password": "dbpassword",
        "host": "dbhost",
        "port": "1433",
        "dbname": "dbname",
        "driver": "ODBC Driver 17 for SQL Server"
    }
}
```

### Redshift
```json
{
    "token": "123asd",
    "destination": "redshift",
    "s3": {
        "arn": "....",
        "bucket": "...."
    },
    "db": {
        "user": "dbuser",
        "password": "dbpassword",
        "host": "dbhost",
        "port": "5432",
        "dbname": "dbname"
    }
}
```

### Local filesystem storage
```json
{
    "token": "123asd",
    "destination": "",
    "local_dest": "/path/to/directory"
}
```
