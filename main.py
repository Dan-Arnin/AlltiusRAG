from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from helper_functions import get_embeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from chain import create_qa_chain, create_checker_chain, check_answer_type_chain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, UnstructuredWordDocumentLoader, PyPDFLoader, JSONLoader
from logger import setup_logger
import config
import json
import os
import logging
from datetime import datetime
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uvicorn

load_dotenv()

logger = setup_logger()
logger.setLevel(logging.INFO)

# Add a stream handler to output logs to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Configure thread pool for concurrent processing
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))  # Default to 4 workers
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
logger.info(f"Configured thread pool with {MAX_WORKERS} workers")

logger.info("Starting the application")
app = FastAPI(title="DMCC Policy Search API", 
              description="API for searching DMCC policies using RAG with LLM", 
              version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (consider restricting this in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global variables
vectorstore = None
conversation_chain = None
directory = config.DIRECTORY

class QueryRequest(BaseModel):
    query: str

def initialize_llm():
    try:
        logger.info("Initializing LLM")
        llm = ChatGoogleGenerativeAI(model="models/gemini-2.0-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
        logger.info("LLM initialized successfully")
        return llm
    except Exception as e:
        logger.error(f"Error initializing LLM: {str(e)}")
        raise

def create_vectorstore(docs):
    logger.info(f"Creating vectorstore with {len(docs)} documents")
    logger.info(f"First two documents: {docs}")
    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(docs, embeddings)
    logger.info("Vectorstore created successfully")
    return vectorstore

def get_chains(vectorstore):
    logger.info("Creating conversation chain")
    llm = initialize_llm()
    chain = create_qa_chain(llm, vectorstore)
    return chain

def get_text_chunks(directory):
    logger.info(f"Processing documents in directory: {directory}")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300, length_function=len)
    chunks = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            logger.info(f"Processing file: {file_path}")
            try:
                if file.endswith('.txt'):
                    # Use UTF-8 encoding with error handling strategy
                    loader = TextLoader(file_path, encoding='utf-8', autodetect_encoding=True)
                elif file.endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                elif file.endswith('.docx'):
                    loader = UnstructuredWordDocumentLoader(file_path)
                elif file.endswith('.json'):
                    loader = JSONLoader(
                        file_path=file_path,
                        jq_schema='.',
                        text_content=False
                    )
                else:
                    logger.warning(f"Skipping unsupported file: {file_path}")
                    continue
                
                document = loader.load()
                logger.info(f"Loaded document from {file_path}")
                
                doc_chunks = text_splitter.split_documents(document)
                logger.info(f"Split {file_path} into {len(doc_chunks)} chunks")
                chunks.extend(doc_chunks)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                logger.error(traceback.format_exc())
                continue
    
    logger.info(f"Processed {len(chunks)} total chunks from all documents")
    return chunks

# Function to process a query with the RAG system
def process_query(query: str):
    current_date = datetime.now().strftime("%Y-%m-%d")
    response = conversation_chain.invoke({
        "input": query,
        "current_date": [SystemMessage(content=current_date)],
    })
    rag_response = response['answer']
    logger.info(f"Generated response for query: '{query[:50]}...'")
    return rag_response

# Initialize the application on startup
@app.on_event("startup")
async def startup_event():
    global vectorstore, conversation_chain
    try:
        logger.info("Initializing application on startup")
        docs = get_text_chunks(directory)
        logger.info(f"Total documents loaded: {len(docs)}")
        if docs:
            logger.info(f"First few documents: {docs[:2]}")
            vectorstore = create_vectorstore(docs)
            conversation_chain = get_chains(vectorstore)
            logger.info("Application initialization complete")
        else:
            logger.warning("No documents were loaded. Check data directory and file formats.")
    except Exception as e:
        logger.critical(f"Failed to initialize application: {str(e)}\n{traceback.format_exc()}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down thread pool executor")
    executor.shutdown(wait=True)
    logger.info("Application shutdown complete")

@app.post("/generate", response_model=dict)
async def generate(request: QueryRequest):
    try:
        global conversation_chain
        query = request.query
        logger.info(f"Received query: '{query[:50]}...'")
        
        if not query:
            logger.error("Empty query received")
            raise HTTPException(status_code=400, detail="Query is required")
        
        if conversation_chain is None:
            logger.error("Conversation chain not initialized")
            raise HTTPException(status_code=500, detail="System not properly initialized")
        
        # Submit query to thread pool for concurrent processing
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, process_query, query)
        
        return {"answer": result}
            
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": str(exc)},
    )

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=3000)


