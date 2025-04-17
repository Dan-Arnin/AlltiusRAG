# Policy Search - Documentation

## Overview

This is a Retrieval-Augmented Generation (RAG) system designed to search through policies and provide accurate answers to user queries. The system uses the Google Gemini 2.0 Flash model with vector search to retrieve relevant information from policy documents.

## Project Structure

- `main.py` - FastAPI web application for handling API requests
- `chain.py` - LangChain chains for question answering and retrieval
- `helper_functions.py` - Utility functions including embedding creation
- `logger.py` - Logging configuration
- `config.py` - Configuration settings
- `.env` - Environment variables
- `data/` - Directory containing policy documents (PDF, DOCX, TXT)
- `requirements.txt` - Project dependencies
- `websiteParser.py`, `url_extractor.py`, `content_extractor_from_urls.py`, `run_scraper.py` - Web scraping utilities

## Requirements

- Python 3.8+
- Google API key with Gemini access
- Dependencies listed in requirements.txt

## Setup Instructions

1. **Clone the repository**

```bash
git clone <repository-url>
cd ODA_Policy_Search
```

2. **Set up a virtual environment**

```bash
# Windows
python -m venv policy
policy\Scripts\activate

# Linux/Mac
python -m venv policy
source policy/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create or update your `.env` file with your Google API key:
```
GOOGLE_API_KEY=your_google_api_key
```

5. **Prepare your policy documents**

Place your policy documents in the `data/` directory. The system supports:
- PDF files (.pdf)
- Word documents (.docx)
- Text files (.txt)
- JSON files (.json)

You can either:
- Manually copy documents to the data directory, or
- Use the included web scraping tools to gather content (see Web Scraping section)

## Running the Application

1. **Start the API server**

```bash
python main.py
```

The server will start on http://0.0.0.0:3006 by default.

2. **Test the API**

You can test the API with a tool like curl or Postman:

```bash
curl -X POST http://localhost:3006/generate \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the health insurance deductible?"}'
```

## API Endpoints

- **POST `/generate`**
  - Request body: `{"query": "your question here"}`
  - Response: `{"answer": "response from the model"}`
  - Used to ask questions about policies

- **GET `/health`**
  - Response: `{"status": "healthy", "timestamp": "2024-04-17T18:00:00.000000"}`
  - Health check endpoint

## Components Overview

### 1. Main Application (`main.py`)

The main FastAPI application that:
- Initializes the Google Gemini LLM
- Processes document chunks from the data directory
- Creates embeddings and vector search capabilities
- Handles user queries through the API endpoint

### 2. Document Processing

The system:
- Loads documents from the data directory
- Splits documents into chunks
- Creates embeddings for vector search
- Retrieves relevant chunks for user queries

### 3. Question Answering Chain (`chain.py`)

The RAG pipeline includes:
- History-aware retriever that reformulates user questions
- Document retriever that finds relevant information
- LLM that generates answers based on retrieved context

### 4. Logging (`logger.py`)

Comprehensive logging system that:
- Creates timestamped log files in the logs directory
- Logs application events, errors, and query processing

## Web Scraping Utilities

The project includes tools to scrape content from websites for use in the RAG system:

### Using the Web Scraper

```bash
python run_scraper.py --url "https://example.com/policies" --depth 3 --delay 2.0 --output "./data"
```

Parameters:
- `--url`: Base URL to scrape (default: https://www.angelone.in/support)
- `--depth`: Maximum depth to crawl (default: 5)
- `--delay`: Delay between requests in seconds (default: 0.5)
- `--output`: Output directory for data (default: ./data)

### Web Scraper Components

- `websiteParser.py` - Main web scraping engine
- `url_extractor.py` - Extracts URLs from web pages
- `content_extractor_from_urls.py` - Extracts content from web pages
- `run_scraper.py` - Command-line interface for web scraping

The scraper generates these output files:
1. `website_data.json` - JSON file containing all extracted data
2. `website_text.txt` - Text file containing all extracted content
3. `visited_urls.txt` - List of all URLs visited during the crawl

## Troubleshooting

### Common Issues

1. **Unicode Errors**: If you experience unicode errors when loading text files, check that your files are correctly encoded (UTF-8 recommended).

2. **Google API Key**: Ensure your Google API key has access to the Gemini models and is correctly set in your .env file.

3. **Document Processing**: If documents aren't being processed correctly, check the logs for specific error messages.

4. **Memory Issues**: Large documents may require more memory. Consider adjusting chunk sizes in the code if you encounter memory problems.

## Advanced Configuration

You can adjust several parameters in the code:

- `MAX_WORKERS`: Controls the number of concurrent threads (default: 4)
- Chunk size and overlap in `RecursiveCharacterTextSplitter` (default: 1200/300)
- Retriever search parameters (default k=30)
- Server port (default: 3006)