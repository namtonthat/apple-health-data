import subprocess


def handler(event, context):
    try:
        # Trigger your DBT job; adjust the command as needed for your environment.
        result = subprocess.run(
            ["dbt", "run"], capture_output=True, text=True, check=True
        )
        return {"statusCode": 200, "body": f"DBT job completed:\n{result.stdout}"}
    except subprocess.CalledProcessError as e:
        return {"statusCode": 500, "body": f"DBT job failed:\n{e.stderr}"}
