from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.python_operator import PythonOperator
from scripts import scrape_song
from airflow.models import Variable

start_date = datetime(2024, 2, 22, 12, 0)
owner = Variable.get("user")
default_args = {
    'owner': owner,
    'start_date': start_date,
    'retries': 1,
    'retry_delay': timedelta(seconds=5)
}

spotify_table_name = 'spotify_table'
with DAG(dag_id='spotify_dag',
         max_active_runs=1,
         default_args=default_args,
         schedule_interval=timedelta(seconds=60),
         catchup=False,
         ) as dag:
    fetch_song = PythonOperator(
        task_id='fetch_spotify_song',
        python_callable=scrape_song,
        provide_context=True,
        op_kwargs={'table_name': spotify_table_name},
        execution_timeout=timedelta(seconds=60),
        retries=1,
        retry_delay=timedelta(seconds=15))
    fetch_song