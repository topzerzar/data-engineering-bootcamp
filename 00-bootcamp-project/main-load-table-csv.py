# Ref: https://cloud.google.com/bigquery/docs/samples/bigquery-load-table-gcs-csv

import json
import os

import pandas as pd

from google.cloud import bigquery
from google.oauth2 import service_account


keyfile = os.environ.get("KEYFILE_PATH")
service_account_info = json.load(open(keyfile))
credentials = service_account.Credentials.from_service_account_info(service_account_info)
project_id = "dataengineer-384509"
client = bigquery.Client(
    project=project_id,
    credentials=credentials,
)

datasets = [
    {
        "name": "addresses",
        "is_require_partition": False
    },
    {
        "name": "events",
        "is_require_partition": True
    },
    {
        "name": "order_items",
        "is_require_partition": False
    },
    {
        "name": "orders",
        "is_require_partition": True
    },
    {
        "name": "products",
        "is_require_partition": False
    },
    {
        "name": "promos",
        "is_require_partition": False
    },
    {
        "name": "users",
        "is_require_partition": True
    }
]

DATASET = 'deb_bootcamp'
DATA_FOLDER = 'data'

for data in datasets:
    print(f"------------------\nFile: {data['name']}")

    file_path = f"{DATA_FOLDER}/{data['name']}.csv"

    with open(file_path, "rb") as csvf:
        table_id = f"{project_id}.{DATASET}.{data['name']}"

        if data['is_require_partition'] is True:
            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                autodetect=True,
                time_partitioning=bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field="created_at",
                )
            )
        else:
            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                autodetect=True,
            )

        job = client.load_table_from_file(csvf, table_id, job_config=job_config)
        job.result()

    table = client.get_table(table_id)
    print(f"Loaded {table.num_rows} rows and {len(table.schema)} columns to {table_id}")
    print('------------------ \n')


    # file_path = f"{DATA_FOLDER}/{fileItem['name']}.csv"
    # print(f"file_path --> {fileItem['name']}")

    # df = pd.read_csv(file_path)
    # if len(fileItem['parse_date']) > 0:
    #     df = pd.read_csv(file_path, parse_dates=fileItem['parse_date'])
    # df.info()

    # table_id = f"{project_id}.{DATASET}.{fileItem['name']}"

    # job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    # if fileItem['is_require_partition'] is True:
    #     job = client.load_table_from_dataframe(df, table_id, job_config=job_config_partition)

    # job.result()

    # table = client.get_table(table_id)
    # print(f"Loaded {table.num_rows} rows and {len(table.schema)} columns to {table_id}")
