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

Settings.llm = Groq(
    model="llama-3.3-70b-versatile", 
    api_key=os.getenv("GROQ_API_KEY")
)

Settings.embed_model = JinaEmbedding(
    api_key=os.getenv("JINA_API_KEY"),
    model="jina-embeddings-v3",
    task="retrieval.passage",
)

PERSIST_DIR = "./storage"

def get_index(is_async: bool = False):
    qdrant_url = os.getenv("QDRANT_CLUSTER_ENDPOINT") or os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if qdrant_url:
        client = qdrant_client.QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        aclient = qdrant_client.AsyncQdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        client = qdrant_client.QdrantClient(path="./storage/qdrant")
        aclient = qdrant_client.AsyncQdrantClient(path="./storage/qdrant")

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
            return VectorStoreIndex.from_documents(
                [doc], 
                storage_context=StorageContext.from_defaults(vector_store=vector_store)
            )
        
        print(f"VectorStoreIndex initialized from {qdrant_url or './storage/qdrant'}")
        return VectorStoreIndex.from_vector_store(vector_store)
    except Exception as e:
        print(f"Error initializing VectorStoreIndex: {e}")
        return VectorStoreIndex.from_documents(
            [], 
            storage_context=StorageContext.from_defaults(vector_store=vector_store)
        )

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
                
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            raise Exception(f"Failed to download file from {url}")

async def get_rag_suggestion(query: str, chat_history: List[Dict] = None) -> str:
    try:
        index = get_index()
        
        history_messages = []
        if chat_history:
            for msg in chat_history:
                role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
                history_messages.append(ChatMessage(role=role, content=msg["content"]))

        reranker = JinaRerank(
            api_key=os.getenv("JINA_API_KEY"),
            model="jina-reranker-v3",
            top_n=3
        )

        chat_engine = index.as_chat_engine(
            chat_mode="condense_plus_context",
            system_prompt=(
                "You are Cluely, an intelligent meeting assistant. "
                "Provide helpful suggestions, hints, or brief recommendations based on the transcript and context. "
                "Keep suggestions concise and relevant to the ongoing conversation."
            ),
            node_postprocessors=[reranker]
        )
        
        response = await chat_engine.achat(query, chat_history=history_messages)
        return str(response)
        
    except Exception as e:
        return f"Maaf, terjadi kesalahan pada sistem RAG: {str(e)}"
