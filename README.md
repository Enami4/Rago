# Document AI Extractor

A Streamlit application that allows users to upload images and PDFs, extract data using OpenAI's Vision API, and export the results to Excel.

## Features

- User authentication (signup/login)
- Drag-and-drop file upload for images and PDFs
- AI-powered data extraction using GPT-4 Vision
- Excel export functionality
- Session-based user management

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. For PDF support, install poppler:
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows
# Download from: https://blog.alivate.com.au/poppler-windows/
```

3. Set your OpenAI API key in `.env`:
```
OPENAI_API_KEY=your_actual_api_key_here
```

4. Run the application:
```bash
streamlit run app.py
```

## Usage

1. Sign up for a new account or login
2. Upload images or PDF files using drag-and-drop
3. Optionally specify custom extraction prompts
4. Click "Extract Data" to process files
5. View results in table or JSON format
6. Download extracted data as Excel file

## Notes

- The app uses GPT-4 Vision for image analysis
- PDF files are converted to images before processing
- User passwords are hashed using bcrypt for security
- Session state is used to maintain login status