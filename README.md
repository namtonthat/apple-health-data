## Apple Health Calendar
A serverless framework that automates the conversion of past daily statistics from Apple Watch into a calendar event.

```mermaid
graph TD
    A[fa:fa-mobile iPhone / Apple Watch] -->|Auto Health Export|B
    B[AWS REST API] --> C[fa:fa-aws AWS Lambda]
    C -->|healthlake.py| D[convert to json to parquet]
    D -->|parse_parquet.py| E[collect latest stats <br> `latest_data.parquet`]
    E -->|create-calendar.py| F[create `ics` file <br> apple-health-calendar.ics]
```
## Project Goals:
- Automate exports from iPhone
- Trigger workflow automatically when AutoExport uploads into S3 endpoint.
- Create `read-only` data available in AWS S3 bucket.
- Files are refreshed in S3 bucket that personal calendar is subscribed to.