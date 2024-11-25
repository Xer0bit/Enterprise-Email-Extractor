# Email Extractor API

A FastAPI application that extracts business emails and business names from website URLs.

## Features
- RESTful API endpoints for bulk URL processing
- Web interface for easy interaction
- CSV export functionality
- Concurrent processing with ThreadPoolExecutor
- Business name extraction from various website elements
- Input validation and error handling
- Detailed logging system
- Swagger UI documentation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/email-extractor.git
cd email-extractor
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:
```bash
python main.py
```

2. Access the web interface:
- Open `http://localhost:8000` in your browser
- Enter URLs to process
- Download results as CSV

3. API Endpoints:
- `POST /extract-emails-bulk/`: Process multiple URLs
- `GET /download-csv/`: Download results as CSV
- API documentation: `http://localhost:8000/docs`

## Requirements
- Python 3.7+
- FastAPI
- BeautifulSoup4
- Requests
- Validators
- Uvicorn

## License
MIT License