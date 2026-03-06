import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, render_template, request, session
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.utilities import SerpAPIWrapper
from dotenv import load_dotenv
from src.prompt import *

load_dotenv()

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.urandom(24)

os.environ["PINECONE_API_KEY"] = os.environ.get('PINECONE_API_KEY')
os.environ["OPENAI_API_KEY"] = os.environ.get('OPENAI_API_KEY')
os.environ["SERPAPI_API_KEY"] = os.environ.get('SERPAPI_API_KEY')  

embeddings = download_hugging_face_embeddings()

docsearch = PineconeVectorStore.from_existing_index(
    index_name="formula-1-chatbot",
    embedding=embeddings
)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})

chatModel = ChatOpenAI(model="gpt-4.1-mini")

search = SerpAPIWrapper() 

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

question_answer_chain = create_stuff_documents_chain(chatModel, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

conversational_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer"
)

def is_context_sufficient(docs) -> bool:
    total_content = " ".join([doc.page_content for doc in docs]).strip()
    return len(total_content) > 100

@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = os.urandom(16).hex()
    return render_template('f1-chat.html')

@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    print("User:", msg)

    session_id = session.get("session_id", "default")

    # Step 1 — check RAG context quality
    retrieved_docs = retriever.invoke(msg)

    # Step 2 — web search via SerpAPI if RAG context is weak
    if is_context_sufficient(retrieved_docs):
        additional_info = "No additional information needed."
        print("Using RAG context")
    else:
        print("RAG insufficient, searching web via SerpAPI...")
        try:
            additional_info = search.run(msg)
            print("SerpAPI results found")
        except Exception as e:
            additional_info = "No additional information available."
            print(f"SerpAPI search failed: {e}")

    # Step 3 — invoke chain
    response = conversational_rag_chain.invoke(
        {
            "input": f"{msg}\n\nAdditional Information: {additional_info}"
        },
        config={"configurable": {"session_id": session_id}}
    )

    print("Bot:", response["answer"])
    return str(response["answer"])

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)