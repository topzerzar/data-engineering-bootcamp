from airflow import DAG
from airflow.utils import timezone
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    'start_date': timezone.datetime(2023, 5, 1)
}

def _world():
    print("world")

with DAG(
    dag_id="everyday",
    default_args=default_args,
    schedule="@daily",
    tags=['DEB'],
    catchup=False,
):

    hello = BashOperator(
        task_id="hello", 
        bash_command="echo 'hello it's me'"
    )

    world = PythonOperator(
        task_id="world",
        python_callable=_world,
    )

    hello >> world