
# Student Performance Analysis System

A web-based application for managing student information, attendance, examination results, and academic performance analytics.

## Features

- Student registration and listing
- Student information validation
- Duplicate email prevention
- Student update and delete APIs
- Attendance management
- Attendance summary and percentage calculation
- Examination marks management
- Class average and student performance summaries
- Grade distribution and subject averages
- Responsive dashboard with charts
- FastAPI backend and SQLAlchemy ORM
- SQLite database
- Automated API tests using pytest

## Technology Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite
- HTML
- CSS
- JavaScript
- Chart.js (if used by the frontend)
- Pytest

## Project Structure

```text
project/
├── app/
│   ├── frontend/
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   ├── tests/
│   │   └── test_main.py
│   ├── __init__.py
│   ├── database.py
│   └── main.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.10 or later
- pip

## Installation

1. Clone or download this repository.
2. Open the project folder in a terminal.
3. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

4. Activate it on Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

## Run the Application

From the project root directory, run:

```bash
python -m uvicorn app.main:app --reload
```

Open the dashboard:

http://127.0.0.1:8000

Open the API documentation:

http://127.0.0.1:8000/docs

## Run Automated Tests

From the project root directory, run:

```bash
python -m pytest app/tests/test_main.py -v
```

The current test suite contains nine tests covering student APIs, validation, attendance, examination results, and error handling.

## Database

The application uses SQLite. The database is created locally when the application initializes.

The local database file is excluded from GitHub using `.gitignore`.

## Project Status

The dashboard and core APIs have been tested locally. Nine automated tests passed in the current development environment.

## Future Improvements

- User authentication and role-based access
- Export reports to CSV or PDF
- Search and filter students
- Improved academic analytics
- Deployment to a hosting platform

## Author

Add your name here.
