
### Process

1. A lambda function URL endpoint invokes the `ingest/lambda.py` handler function  to save the Apple Health export as is within the defined `S3` bucket.
2. `dbt` alongside `duckdb` is used to transform and unnest this data to the format required for displaying information
3. `calendar/lambda.py` creates an `ics` calendar file from the output `S3` buckets. You can subscribe to this `ics` calendar to integrate with any existing Calendar service.

### Entity Relationship Diagram

  ```mermaid
  classDiagram
      %% EventConfig holds the YAML configuration for a specific event type
      class EventConfig {
        +name: str
        +title_template: str
        +description_template: str
        +required_metrics: list[str]
        +from_yaml(yaml_path: Path, group_name: str): EventConfig
      }

      %% ConfigManager loads and manages EventConfig instances from YAML
      class ConfigManager {
        +config_path: str
        +event_configs: dict[str, EventConfig]
        +get_config(group_name: str): EventConfig
      }

      %% DataLoader loads a Parquet file from S3 and returns a DataFrame
      class DataLoader {
        +load_from_s3(s3_bucket: str, s3_path: str): pl.DataFrame
      }

      %% EventFactory creates calendar Event objects using DataFrame data and EventConfig
      class EventFactory {
        +create_event_for_date(event_date: date, df: pl.DataFrame, config: EventConfig): Optional[Event]
        -_extract_metrics(df: pl.DataFrame): dict[str, float | str]
        -_extract_units(df: pl.DataFrame): dict[str, str]
      }

      %% CalendarStorage handles saving Calendar objects locally and to S3
      class CalendarStorage {
        +s3_bucket: Optional[str]
        +save_local(calendar: Calendar, filename: str): str
        +save_to_s3(calendar: Calendar, filename: str, ics_content: Optional[str]): Optional[str]
      }

      %% CalendarGenerator coordinates the entire calendar generation process
      class CalendarGenerator {
        +config_path: str
        +s3_bucket: Optional[str]
        +calendar: Calendar
        +config_manager: ConfigManager
        +storage: CalendarStorage
        +add_events_from_s3(s3_bucket: str, s3_path: str, group_name: str): int
        +save_calendar(filename: str, save_to_s3: bool): None
      }

      %% Calendar and Event are from the ics library
      class Calendar {
        +events: set(Event)
      }

      class Event {
        +name: str
        +description: str
        +begin: datetime
        +make_all_day(): void
      }

      %% Relationships
      ConfigManager "1" --> "many" EventConfig : manages
      EventFactory ..> EventConfig : uses
      EventFactory ..> Event : creates
      CalendarGenerator --> ConfigManager : has
      CalendarGenerator --> CalendarStorage : has
      CalendarGenerator --> Calendar : maintains
      CalendarGenerator ..> DataLoader : uses
  ```

### IAM Role Permissions for Github Actions

To have an automated scheduled process via Github Actions, you need to create a IAM role with the following permissions (replacing the values `AWS_REGION` and `AWS_ACCOUNT_ID` with your own)

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowECRActions",
            "Effect": "Allow",
            "Action": [
                "ecr:DescribeRepositories",
                "ecr:ListTagsForResource",
                "ecr:DescribeImages"
            ],
            "Resource": [
                "arn:aws:ecr:<AWS_REGION>:<AWS_ACCOUNT_ID>:repository/lambda_dbt_repo",
                "arn:aws:ecr:<AWS_REGION>:<AWS_ACCOUNT_ID>:repository/lambda_ingest_repo"
            ]
        },
        {
            "Sid": "AllowIAMRoleActions",
            "Effect": "Allow",
            "Action": [
                "iam:GetRole",
                "iam:ListRolePolicies",
                "iam:ListAttachedRolePolicies"
            ],
            "Resource": [
                "arn:aws:iam::<AWS_ACCOUNT_ID>:role/lambda_ingest_role",
                "arn:aws:iam::<AWS_ACCOUNT_ID>:role/lambda_dbt_role"
            ]
        },
        {
            "Sid": "AllowIAMPolicyActions",
            "Effect": "Allow",
            "Action": [
                "iam:GetPolicy",
                "iam:GetPolicyVersion"
            ],
            "Resource": "arn:aws:iam::<AWS_ACCOUNT_ID>:policy/lambda_ingest_s3_policy"
        },
        {
            "Sid": "AllowLambdaActions",
            "Effect": "Allow",
            "Action": [
                "lambda:GetFunction",
                "lambda:ListTags",
                "lambda:GetFunctionConfiguration",
                "lambda:ListVersionsByFunction",
                "lambda:GetPolicy",
                "lambda:GetFunctionUrlConfig",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration"
            ],
            "Resource": [
                "arn:aws:lambda:<AWS_REGION>:<AWS_ACCOUNT_ID>:function:trigger_dbt_job",
                "arn:aws:lambda:<AWS_REGION>:<AWS_ACCOUNT_ID>:function:ingest_health_data"
            ]
        }
    ]
}

```
