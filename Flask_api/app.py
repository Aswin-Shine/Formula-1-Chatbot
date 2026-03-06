import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, render_template, jsonify, request
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SerpAPIWrapper
from dotenv import load_dotenv
from src.prompt import *

load_dotenv()

os.environ["PINECONE_API_KEY"] = os.environ.get('PINECONE_API_KEY')
os.environ["OPENAI_API_KEY"] = os.environ.get('OPENAI_API_KEY')
os.environ["SERPAPI_API_KEY"] = os.environ.get('SERPAPI_API_KEY')

app = Flask(__name__, template_folder='../templates')

embeddings = download_hugging_face_embeddings()

docsearch = PineconeVectorStore.from_existing_index(
    index_name="formula-1-chatbot",
    embedding=embeddings
)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})

chatModel = ChatOpenAI(model="gpt-4.1-mini")

# Web search tool
search = SerpAPIWrapper()

def is_context_relevant(docs, threshold=3):
    """Check if retrieved docs have enough content"""
    total_content = " ".join([doc.page_content for doc in docs])
    return len(total_content.strip()) > threshold

def get_answer(user_input):
    # Step 1 — try RAG first
    retrieved_docs = retriever.invoke(user_input)
    
    web_results = "No web search needed."

    # Step 2 — if RAG context is weak, search the web
    if not is_context_relevant(retrieved_docs):
        print("RAG context insufficient, searching the web...")
        web_results = search.run(user_input)

    # Step 3 — build prompt with both context and web results
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(chatModel, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    response = rag_chain.invoke({
        "input": user_input,
        "web_results": web_results
    })

    return response["answer"]


@app.route("/")
def index():
    return render_template('f1-chat.html')


@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    print("User:", msg)
    answer = get_answer(msg)
    print("Bot:", answer)
    return str(answer)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)