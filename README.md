## Apple Health Calendar
Simple python script that automates the conversion of past daily statistics from Apple Watch into a calendar event.

```mermaid
graph TD
    A[fa:fa-mobile iPhone / Apple Watch] -->|Auto Health Export| B[AWS S3 Bucket as CSV]
    B --> C[fa:fa-aws AWS Lambda]
```
