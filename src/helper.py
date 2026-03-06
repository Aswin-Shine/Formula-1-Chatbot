from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from typing import List
from langchain.schema import Document
import os

# Extract Data From PDF and CSV Files
def load_pdf_file(data):
    pdf_documents = []
    csv_documents = []

    # Load PDFs
    if any(f.endswith('.pdf') for f in os.listdir(data)):
        pdf_loader = DirectoryLoader(data, glob="*.pdf", loader_cls=PyPDFLoader)
        pdf_documents = pdf_loader.load()

    # Load CSVs
    if any(f.endswith('.csv') for f in os.listdir(data)):
        csv_loader = DirectoryLoader(
            data,
            glob="*.csv",
            loader_cls=CSVLoader,
            loader_kwargs={
                "encoding": "latin-1"  # ✅ handles special characters
            }
        )
        csv_documents = csv_loader.load()

    documents = pdf_documents + csv_documents
    return documents

def filter_to_minimal_docs(docs: List[Document]) -> List[Document]:
    """
    Given a list of Document objects, return a new list of Document objects
    containing only 'source' in metadata and the original page_content.
    """
    minimal_docs: List[Document] = []
    for doc in docs:
        src = doc.metadata.get("source")
        minimal_docs.append(
            Document(
                page_content=doc.page_content,
                metadata={"source": src}
            )
        )
    return minimal_docs

# Split the Data into Text Chunks
def text_split(extracted_data):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    text_chunks = text_splitter.split_documents(extracted_data)
    return text_chunks

# Download the Embeddings from HuggingFace
def download_hugging_face_embeddings():
    model_path = "/app/models/all-MiniLM-L6-v2"
    
    if os.path.exists(model_path):
        # inside Docker — load from local path
        embeddings = HuggingFaceEmbeddings(model_name=model_path)
    else:
        # running locally — download from HuggingFace
        embeddings = HuggingFaceEmbeddings(
            model_name='sentence-transformers/all-MiniLM-L6-v2'
        )
    return embeddings