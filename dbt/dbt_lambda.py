import json
import subprocess
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()


def handler(event, context):
    # Log the incoming S3 event
    logger.info("Received S3 event", extra=event)

    dbt_project_path = "/var/dbt_project"

    try:
        result = subprocess.run(
            ["dbt", "run"], cwd=dbt_project_path, capture_output=True, text=True
        )

        if result.returncode == 0:
            logger.info("DBT job succeeded", extra={"output": result.stdout})
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"message": "DBT job executed", "output": result.stdout}
                ),
            }
        else:
            logger.error("DBT job failed", extra={"error": result.stderr})
            return {"statusCode": 500, "body": json.dumps({"error": result.stderr})}
    except Exception as e:
        logger.exception("Exception when executing DBT job")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
