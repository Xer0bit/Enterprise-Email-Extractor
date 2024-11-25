import re
import requests
import logging
import csv
from io import StringIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict
from concurrent.futures import ThreadPoolExecutor
import validators
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel, AnyHttpUrl, ValidationError
import uvicorn
from functools import wraps

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_extractor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def extract_business_name(url: str, soup: BeautifulSoup) -> str:
    try:
        # Try to get business name from title
        title = soup.title.string if soup.title else ""
        
        # Try meta tags
        meta_desc = soup.find('meta', {'name': ['description', 'og:site_name']})
        if meta_desc:
            meta_content = meta_desc.get('content', '')
        else:
            meta_content = ""
            
        # Try h1 headers
        h1_text = soup.find('h1').text if soup.find('h1') else ""
        
        # Try website domain
        domain = urlparse(url).netloc.split('.')[-2]
        
        # Prioritize the sources
        potential_names = [
            title.split('|')[0].split('-')[0].strip() if title else "",
            meta_content.split('|')[0].strip(),
            h1_text.strip(),
            domain.capitalize()
        ]
        
        # Return the first non-empty name that's reasonable in length
        for name in potential_names:
            if name and 2 < len(name) < 50:
                return name
                
        return domain.capitalize()
    except Exception as e:
        logger.error(f"Error extracting business name: {str(e)}")
        return urlparse(url).netloc.split('.')[-2].capitalize()

def extract_data_from_url(url: str) -> dict:
    data = {'emails': set(), 'business_name': ''}
    try:
        logger.info(f"Processing URL: {url}")
        if not validators.url(url):
            print(f"Invalid URL: {url}")
            return data

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract emails
        text_content = soup.get_text()
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_emails = re.findall(email_pattern, text_content)
        data['emails'].update(found_emails)
        
        # Extract business name
        data['business_name'] = extract_business_name(url, soup)
        
        logger.info(f"Found {len(data['emails'])} emails and business name '{data['business_name']}' from {url}")

    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
    
    return data

def process_urls(urls: List[str]) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(extract_data_from_url, url): url for url in urls}
        for future in futures:
            url = futures[future]
            results[url] = future.result()
    return results

# Remove URLInput class and EmailResponse class since they're no longer needed

class URLBulkInput(BaseModel):
    urls: List[str]  # Changed from HttpUrl to str for initial validation

    class Config:
        arbitrary_types_allowed = True

class BulkEmailResponse(BaseModel):
    results: Dict[str, Dict[str, object]]

SECRET_WORD = "your_secret_word_here"  # Change this to your desired secret word
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def require_auth(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        api_key = request.cookies.get(API_KEY_NAME)
        if not api_key or api_key != SECRET_WORD:
            return RedirectResponse(url="/login")
        return await func(*args, **kwargs)
    return wrapper

app = FastAPI(
    title="Bulk Email Extractor API",
    description="API to extract business emails from multiple websites",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/login", response_class=HTMLResponse)
async def get_login():
    return """
    <html>
        <head>
            <title>Login - Email Extractor</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                    font-family: 'Segoe UI', system-ui, sans-serif;
                }
                body {
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    background: white;
                    padding: 2.5rem;
                    border-radius: 12px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 400px;
                    margin: 1rem;
                }
                h2 {
                    color: #2d3748;
                    margin-bottom: 1.5rem;
                    font-size: 1.5rem;
                    text-align: center;
                }
                .input-group {
                    margin-bottom: 1.5rem;
                }
                input {
                    width: 100%;
                    padding: 0.75rem 1rem;
                    border: 2px solid #e2e8f0;
                    border-radius: 8px;
                    font-size: 1rem;
                    transition: all 0.3s ease;
                }
                input:focus {
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
                }
                button {
                    width: 100%;
                    padding: 0.75rem 1rem;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 1rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                button:hover {
                    background: #5a67d8;
                }
                button:active {
                    transform: scale(0.98);
                }
                .error {
                    color: #e53e3e;
                    margin-top: 0.5rem;
                    font-size: 0.875rem;
                    display: none;
                }
                button.loading {
                    background: #cbd5e0;
                    cursor: not-allowed;
                }
                .loading-spinner {
                    display: none;
                    width: 20px;
                    height: 20px;
                    border: 3px solid #f3f3f3;
                    border-top: 3px solid #667eea;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Welcome Back</h2>
                <form id="loginForm">
                    <div class="input-group">
                        <input type="password" 
                               id="secretWord" 
                               placeholder="Enter secret word"
                               autocomplete="current-password">
                        <div class="error" id="errorMessage">Invalid secret word</div>
                    </div>
                    <button type="submit" id="submitButton">
                        <span>Login</span>
                        <div class="loading-spinner" id="spinner"></div>
                    </button>
                </form>
            </div>
            <script>
                const form = document.getElementById('loginForm');
                const button = document.getElementById('submitButton');
                const spinner = document.getElementById('spinner');
                const errorMessage = document.getElementById('errorMessage');

                form.onsubmit = async (e) => {
                    e.preventDefault();
                    
                    // Reset state
                    errorMessage.style.display = 'none';
                    button.classList.add('loading');
                    button.querySelector('span').style.display = 'none';
                    spinner.style.display = 'block';
                    
                    try {
                        const response = await fetch('/verify-login', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                secret: document.getElementById('secretWord').value
                            })
                        });
                        
                        if (response.ok) {
                            window.location.href = '/';
                        } else {
                            throw new Error('Invalid secret word');
                        }
                    } catch (error) {
                        errorMessage.style.display = 'block';
                        button.classList.remove('loading');
                        button.querySelector('span').style.display = 'block';
                        spinner.style.display = 'none';
                    }
                };
            </script>
        </body>
    </html>
    """

@app.post("/verify-login")
async def verify_login(request: Request):
    data = await request.json()
    if data.get('secret') == SECRET_WORD:
        response = JSONResponse({"status": "success"})
        response.set_cookie(API_KEY_NAME, SECRET_WORD)
        return response
    raise HTTPException(status_code=401, detail="Invalid secret word")

@app.get("/", response_class=HTMLResponse)
@require_auth
async def get_web_interface(request: Request):
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())

# Add global variable to store results
extraction_history = {}

# Remove @app.post("/extract-email/") endpoint since it's no longer needed

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid URL format. Please ensure all URLs include http:// or https://"}
    )

@app.post("/extract-emails-bulk/", response_model=BulkEmailResponse)
@require_auth
async def extract_bulk_urls(request: Request, urls_input: URLBulkInput):
    # Validate URLs manually
    valid_urls = []
    for url in urls_input.urls:
        # Add http:// if protocol is missing
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        if validators.url(url):
            valid_urls.append(url)
        else:
            raise HTTPException(status_code=422, detail=f"Invalid URL format: {url}")
    
    if not valid_urls:
        raise HTTPException(status_code=422, detail="No valid URLs provided")
    
    results = process_urls(valid_urls)
    extraction_history.update(results)
    return BulkEmailResponse(results=results)

@app.get("/download-csv/")
@require_auth
async def download_csv(request: Request):
    logger.info("Generating CSV file for download")
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["URL", "Business Name", "Emails"])
    
    for url, data in extraction_history.items():
        writer.writerow([
            url, 
            data['business_name'],
            ", ".join(data['emails'])
        ])
    
    output.seek(0)
    
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=extracted_emails.csv"}
    )
    
    logger.info("CSV file generated successfully")
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)