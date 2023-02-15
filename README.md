## Apple Health Calendar
A serverless framework that automates the conversion of past daily statistics from Apple Watch into a calendar event.

```mermaid
graph TD
    A[fa:fa-mobile iPhone / Apple Watch] -->|Auto Health Export|B
    B[AWS Rest API <br> s3 bucket `/syncs`] --> C[fa:fa-aws AWS Lambda]
    C -->|create-calendar.py| D[apple-health-calendar.ics]
    C -->|parse_as_parquet.py| E[latest_data.parquet]
```
## Project Goals:
- Automate exports from iPhone
- Trigger workflow automatically when AutoExport uploads into S3 endpoint.
- Files are refreshed in S3 bucket that personal Google Calendar is subscribed to.