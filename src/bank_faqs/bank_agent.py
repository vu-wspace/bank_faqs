import truststore
from dotenv import load_dotenv
from langchain_groq import ChatGroq

truststore.inject_into_ssl()
load_dotenv()

groq_llm = ChatGroq(
    model='qwen/qwen3.8-27b',
    temperature=0
)
