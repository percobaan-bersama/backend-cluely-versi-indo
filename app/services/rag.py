import os
from typing import List, Dict
from llama_index.llms.groq import Groq
from llama_index.embeddings.jinaai import JinaEmbedding
from llama_index.postprocessor.jinaai_rerank import JinaRerank
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client
from llama_index.core.settings import Settings
from llama_index.core.llms import ChatMessage, MessageRole
from dotenv import load_dotenv

load_dotenv()

Settings.embed_model = JinaEmbedding(
    api_key=os.getenv("JINA_API_KEY"),
    model="jina-embeddings-v3",
    task="retrieval.passage",
)

from app.services.llm import MODELS

def get_llm(model_name: str):
    return Groq(
        model=model_name,
        api_key=os.getenv("GROQ_API_KEY")
    )

Settings.llm = get_llm(MODELS[0])


_q_client = None
_aq_client = None
_reranker = None
_index_empty_cache = None 

PERSIST_DIR = "./storage"
_index = None

def _get_qdrant_clients():
    global _q_client, _aq_client
    if _q_client is None:
        qdrant_url = os.getenv("QDRANT_CLUSTER_ENDPOINT") or os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        if qdrant_url:
            _q_client = qdrant_client.QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            _aq_client = qdrant_client.AsyncQdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            _q_client = qdrant_client.QdrantClient(path="./storage/qdrant")
            _aq_client = qdrant_client.AsyncQdrantClient(path="./storage/qdrant")
    return _q_client, _aq_client

def get_index(is_async: bool = False):
    global _index
    if _index is not None:
        return _index
        
    client, aclient = _get_qdrant_clients()
    collection_name = "cluely_meetings"
    
    try:
        
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if not exists:
            from qdrant_client.http.models import Distance, VectorParams
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )
    except Exception as e:
        print(f"Error checking/creating Qdrant collection: {e}")

    vector_store = QdrantVectorStore(
        client=client, 
        aclient=aclient, 
        collection_name=collection_name
    )
    
    try:
        collection_info = client.get_collection(collection_name)
        if collection_info.points_count == 0:
            from llama_index.core import Document
            print(f"Collection {collection_name} is empty. Seeding initial document.")
            doc = Document(text="Cluely is a meeting assistant developed to help with transcripts and suggestions.")
            _index = VectorStoreIndex.from_documents(
                [doc], 
                storage_context=StorageContext.from_defaults(vector_store=vector_store)
            )
            return _index
        
        print(f"VectorStoreIndex initialized from Qdrant")
        _index = VectorStoreIndex.from_vector_store(vector_store)
        return _index
    except Exception as e:
        print(f"Error initializing VectorStoreIndex: {e}")
        _index = VectorStoreIndex.from_documents(
            [], 
            storage_context=StorageContext.from_defaults(vector_store=vector_store)
        )
        return _index

async def ingest_document_from_url(url: str, filename: str):
    import httpx
    import tempfile
    from llama_index.core import SimpleDirectoryReader
    
    index = get_index()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            
            try:
                reader = SimpleDirectoryReader(input_files=[tmp_path])
                documents = reader.load_data()
                
                for doc in documents:
                    doc.metadata = {"filename": filename, "source": url}
                    index.insert(doc)
                
                
                global _index_empty_cache
                _index_empty_cache = False
                
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            raise Exception(f"Failed to download file from {url}")

async def get_rag_suggestion(query: str, chat_history: List[Dict] = None) -> str:
    global _reranker
    if _reranker is None:
        _reranker = JinaRerank(
            api_key=os.getenv("JINA_API_KEY"),
            model="jina-reranker-v3",
            top_n=3
        )

    last_error = None
    for model_name in MODELS:
        try:
            Settings.llm = get_llm(model_name)
            index = get_index()
            
            history_messages = []
            if chat_history:
                for msg in chat_history:
                    role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
                    history_messages.append(ChatMessage(role=role, content=msg["content"]))

            chat_engine = index.as_chat_engine(
                chat_mode="context",
                system_prompt=(
                    "Anda berperan sebagai seorang Calon Karyawan (Candidate/Interviewee) yang sedang menjalani proses wawancara kerja. "
                    "Lawan bicara Anda adalah pihak HR (Human Resources) atau pewawancara."
                    "\n\nInstruksi Penting:"
                    "\n1. Gunakan KONTEKS yang diberikan sebagai sumber utama jawaban Anda—anggaplah informasi tersebut adalah pengalaman, latar belakang, dan keahlian Anda sendiri."
                    "\n2. Jika informasi tertentu tidak ada dalam konteks, jawablah dengan jujur sesuai logika seorang kandidat yang berusaha memberikan kesan positif tanpa berbohong."
                    "\n3. Jawablah secara ringkas, profesional, dan gunakan Bahasa Indonesia yang sopan (formal)."
                    "\n4. Pastikan Anda menunjukkan antusiasme terhadap posisi yang sedang dilamar."
                ),
                node_postprocessors=[_reranker]
            )
            
            response = await chat_engine.astream_chat(query, chat_history=history_messages)
            return response
        except Exception as e:
            print(f"Error with RAG model {model_name}: {e}")
            last_error = e
            continue
            
    
    async def error_generator():
        yield f"Maaf, terjadi kesalahan pada sistem RAG: {str(last_error)}"
    return error_generator()

async def is_index_empty() -> bool:
    global _index_empty_cache
    if _index_empty_cache is not None:
        return _index_empty_cache

    client, aclient = _get_qdrant_clients()
    collection_name = "cluely_meetings"
    try:
        
        collections = (await aclient.get_collections()).collections
        exists = any(c.name == collection_name for c in collections)
        if not exists:
            _index_empty_cache = True
            return True
            
        collection_info = await aclient.get_collection(collection_name)
        _index_empty_cache = collection_info.points_count <= 1
        return _index_empty_cache
    except Exception as e:
        print(f"Error in is_index_empty: {e}")
        return True

async def initialize_rag_service():
    print("cold start di background dimulai")
    try:
        get_index()
        await is_index_empty()
        print("cold start di background selesai")
    except Exception as e:
        print(f"cold start gagal: {e}")
