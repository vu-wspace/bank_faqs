import bank_faqs  # noqa: F401 - phải import đầu tiên: nạp fix DLL cho torch trên Windows (xem __init__.py)
import truststore
import os
import uuid
import pandas as pd
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from pyvi import ViTokenizer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer
from bank_faqs.utils.get_conversation_by_id import OUTPUT_FILE

truststore.inject_into_ssl()
load_dotenv()

QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
COLLECTION = 'cskh_bkai'
MODEL_NAME = 'bkai-foundation-models/vietnamese-bi-encoder'
VECTOR_SIZE = 768

class BkaiEmbeddings(Embeddings):
    def __init__(self, model_name: str = MODEL_NAME):
        self.model = SentenceTransformer(model_name)

    def _enc(self, texts):
        texts = [ViTokenizer.tokenize(t) for t in texts]
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_documents(self, texts):
        return self._enc(texts)

    def embed_query(self, text):
        return self._enc([text])[0]

def get_vector_store(emb: Embeddings | None = None) -> QdrantVectorStore:
    client = QdrantClient(url=QDRANT_URL)
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    return QdrantVectorStore(client=client, collection_name=COLLECTION, embedding=emb or BkaiEmbeddings())

def ingest(db: QdrantVectorStore) -> int:
    df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
    docs = [
        Document(page_content=q, metadata={'answer': a, 'chu_de': c, 'hoi_thoai_id': i})
        for i, q, a, c in zip(df['hoi_thoai_id'], df['question'], df['answer'], df['chu_de'])
    ]
    ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, i)) for i in df['hoi_thoai_id']]
    db.add_documents(docs, ids=ids)
    return len(docs)

def get_retriever(k: int = 3):
    return get_vector_store().as_retriever(search_kwargs={'k': k})

def main():
    print('1. Đang kết nối Qdrant + tải model...', flush=True)
    db = get_vector_store()

    print('2. Đang nạp dữ liệu...', flush=True)
    n = ingest(db)
    print(f"3. Đã nạp {n} hội thoại vào '{COLLECTION}'", flush=True)

    retriever = db.as_retriever(search_kwargs={'k': 3})
    for h in retriever.invoke('quên mật khẩu app ngân hàng'):
        print(h.metadata['hoi_thoai_id'], '|', h.page_content[:60])

if __name__ == "__main__":
    main()
