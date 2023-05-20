from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils import timezone

import requests
import csv
import json
import os
import configparser

from google.oauth2 import service_account
from google.cloud import storage, bigquery


DATA = "addresses"
DATA_FOLDER = "/opt/airflow/dags/data"
SECRET_FOLDER = "/opt/airflow/dags/secret"
BUSINESS_DOMAIN = "greenery"
REGION = "asia-southeast1"
PROJECT_ID = "dataengineer-384509"
BUCKET_NAME = "deb-greenery-datapipeline"

parser = configparser.ConfigParser()
parser.read(f"{SECRET_FOLDER}/pipeline.conf")


def _extract_data(ds):
    print("##### Start get data from API #####")
    host = parser.get("api_config", "host")
    port = parser.get("api_config", "port")
    api_url = f"http://{host}:{port}"

    response = requests.get(f"{api_url}/addresses?created_at={ds}")
    data = response.json()

    with open(f"{DATA_FOLDER}/{DATA}-{ds}.csv", "w") as f:
        writer = csv.writer(f)
        header = [ "address_id", "address", "zipcode", "state", "country"]
        writer.writerow(header)

        print("found data", len(data) , " records")
        for each in data:
            item = [
                each["address_id"],
                each["address"],
                each["zipcode"],
                each["state"],
                each["country"]
            ]
            writer.writerow(item)

    print("##### End get data from API #####")

def _load_data_to_gcs(ds):
    print(f"##### Start upload data: {DATA} , date: {ds} to GCS #####")
    keyfile_gcs = f"{SECRET_FOLDER}/dataengineer-service-account-gcs.json"
    service_account_info_gcs = json.load(open(keyfile_gcs))
    credentials_gcs = service_account.Credentials.from_service_account_info(
        service_account_info_gcs
    )

    storage_client = storage.Client(
        project=PROJECT_ID,
        credentials=credentials_gcs,
    )
    bucket = storage_client.bucket(BUCKET_NAME)

    file_path = f"{DATA_FOLDER}/{DATA}-{ds}.csv"
    destination_blob_name = f"{BUSINESS_DOMAIN}/{DATA}/{DATA}-{ds}.csv"
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    print(f"##### END upload data: {DATA} , date: {ds} to GCS #####")


def _load_data_from_gcs_to_bigquery(ds):
    print(f"##### Start load data: {DATA} , date: {ds} from GCS to Big Query #####")
    keyfile_bigquery = f"{SECRET_FOLDER}/dataengineer-gcs-and-bigquery-service-account.json"
    service_account_info_bigquery = json.load(open(keyfile_bigquery))
    credentials_bigquery = service_account.Credentials.from_service_account_info(
        service_account_info_bigquery
    )

    bigquery_client = bigquery.Client(
        project=PROJECT_ID,
        credentials=credentials_bigquery,
        location=REGION,
    )
    table_id = f"{PROJECT_ID}.deb_bootcamp.{DATA}"
    job_config = bigquery.LoadJobConfig(
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.CSV,
        autodetect=True,
    )
    destination_blob_name = f"{BUSINESS_DOMAIN}/{DATA}/{DATA}-{ds}.csv"
    job = bigquery_client.load_table_from_uri(
        f"gs://{BUCKET_NAME}/{destination_blob_name}",
        table_id,
        job_config=job_config,
        location=REGION,
    )
    job.result()

    table = bigquery_client.get_table(table_id)
    print(f"Loaded {table.num_rows} rows and {len(table.schema)} columns to {table_id}")
    print(f"##### End load data: {DATA} , date: {ds} from GCS to Big Query #####")



default_args = {
    "owner": "airflow",
	"start_date": timezone.datetime(2023, 5, 1),  # Set an appropriate start date here
}
with DAG(
    dag_id="greenery_addresses_data_pipeline",
    default_args=default_args,
    schedule=None,  # Set your schedule here
    catchup=False,
    tags=["DEB", "2023", "greenery"],
):

    # Extract data from Postgres, API, or SFTP
    extract_data = PythonOperator(
        task_id="extract_data",
        python_callable=_extract_data,
        op_kwargs={"ds": "{{ ds }}"}
    )

    # Load data to GCS
    load_data_to_gcs = PythonOperator(
        task_id="load_data_to_gcs",
        python_callable=_load_data_to_gcs,
        op_kwargs={"ds": "{{ ds }}"}
    )

    # Load data from GCS to BigQuery
    load_data_from_gcs_to_bigquery = PythonOperator(
        task_id="load_data_from_gcs_to_bigquery",
        python_callable=_load_data_from_gcs_to_bigquery,
        op_kwargs={"ds": "{{ ds }}"}
    )

    # Task dependencies
    extract_data >> load_data_to_gcs >> load_data_from_gcs_to_bigquery