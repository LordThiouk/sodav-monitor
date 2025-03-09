# Reports Router Module

This module handles all operations related to report generation and management in the SODAV Monitor system.

## Structure

The reports router is divided into three main components:

1. **Core (`core.py`)**: Basic CRUD operations for reports
2. **Generation (`generation.py`)**: Report generation functionality
3. **Subscriptions (`subscriptions.py`)**: Report subscription management

## Endpoints

### Core Endpoints

- `GET /api/reports`: Get a list of reports
- `POST /api/reports`: Create a new report
- `GET /api/reports/{report_id}`: Get a specific report
- `GET /api/reports/{report_id}/status`: Get the status of a report
- `GET /api/reports/{report_id}/download`: Download a report
- `DELETE /api/reports/{report_id}`: Delete a report
- `PUT /api/reports/{report_id}/status`: Update the status of a report

### Generation Endpoints

- `POST /api/reports/generate/daily`: Generate a daily report
- `POST /api/reports/generate/monthly`: Generate a monthly report
- `POST /api/reports/generate`: Generate a custom report
- `POST /api/reports/send/{report_id}`: Send a report by email

### Subscription Endpoints

- `POST /api/reports/subscriptions`: Create a new subscription
- `GET /api/reports/subscriptions`: Get a list of subscriptions
- `GET /api/reports/subscriptions/{subscription_id}`: Get a specific subscription
- `PUT /api/reports/subscriptions/{subscription_id}`: Update a subscription
- `DELETE /api/reports/subscriptions/{subscription_id}`: Delete a subscription
- `GET /api/reports/subscriptions/by-email`: Get subscriptions by email

## Authentication

All endpoints require authentication. The user must be logged in and have a valid JWT token.

## Report Types

The system supports several types of reports:

- **Daily**: Statistics for a single day
- **Weekly**: Statistics for a week
- **Monthly**: Statistics for a month
- **Comprehensive**: Detailed statistics for a custom period

## Report Formats

Reports can be generated in various formats:

- **PDF**: Portable Document Format
- **XLSX**: Excel Spreadsheet
- **CSV**: Comma-Separated Values
- **JSON**: JavaScript Object Notation

## Background Tasks

Report generation is performed in the background to avoid blocking the API. The user can check the status of a report using the status endpoint.

## Dependencies

This module depends on:

- `backend.models.database`: Database access
- `backend.models.models`: Data models
- `backend.utils.auth`: Authentication utilities
- `backend.utils.file_manager`: File management utilities
- `backend.reports.generator`: Report generation utilities

## Usage Example

```python
# Create a new report
report_data = {
    "report_type": "DAILY",
    "format": "PDF",
    "start_date": "2023-01-01T00:00:00",
    "end_date": "2023-01-02T00:00:00",
    "include_graphs": True,
    "language": "fr"
}
response = await client.post("/api/reports", json=report_data, headers=auth_headers)
report = response.json()

# Check the status of a report
response = await client.get(f"/api/reports/{report['id']}/status", headers=auth_headers)
status = response.json()

# Download a report
response = await client.get(f"/api/reports/{report['id']}/download", headers=auth_headers)
with open("report.pdf", "wb") as f:
    f.write(response.content)

# Create a subscription
subscription_data = {
    "name": "Daily Report",
    "email": "user@example.com",
    "frequency": "daily",
    "report_type": "DAILY",
    "format": "PDF",
    "include_graphs": True,
    "language": "fr"
}
response = await client.post("/api/reports/subscriptions", json=subscription_data, headers=auth_headers)
subscription = response.json()
``` 