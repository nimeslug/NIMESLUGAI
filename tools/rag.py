"""
RAG (Retrieval-Augmented Generation) module for Nimeslug.
Loads PDF documents, embeds them, stores in ChromaDB, and searches semantically.
"""

import os
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader


# ─── Configuration ───────────────────────────────────────────
KNOWLEDGE_BASE_DIR = Path("knowledge_base")
CHROMA_DB_DIR = Path("chroma_db")
COLLECTION_NAME = "nimeslug_kb"

# Multilingual embedding model — works for both TR and EN
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Chunking parameters
CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 150     # overlap between chunks (preserves context)


# ─── ChromaDB Client (lazy initialization) ───────────────────
_client = None
_collection = None


def get_collection():
    """Get or create the ChromaDB collection (singleton pattern)."""
    global _client, _collection
    
    if _collection is not None:
        return _collection
    
    CHROMA_DB_DIR.mkdir(exist_ok=True)
    
    _client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    
    # Use a multilingual sentence transformer for TR + EN support
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "Nimeslug knowledge base"},
    )
    
    return _collection


# ─── PDF Loading ─────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """
    Extract text from a PDF, returning a list of {page, text} dicts.
    """
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    return pages


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks for better semantic search.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks


# ─── Indexing ────────────────────────────────────────────────
def index_pdf(pdf_path: Path) -> dict:
    """
    Extract, chunk, embed, and store a PDF in the knowledge base.
    Returns metadata about the indexing operation.
    """
    if not pdf_path.exists():
        return {"error": f"File not found: {pdf_path}"}
    
    collection = get_collection()
    pages = extract_text_from_pdf(pdf_path)
    
    if not pages:
        return {"error": f"No extractable text in {pdf_path.name}"}
    
    documents = []
    metadatas = []
    ids = []
    
    for page_info in pages:
        page_num = page_info["page"]
        chunks = chunk_text(page_info["text"])
        
        for chunk_idx, chunk in enumerate(chunks):
            doc_id = f"{pdf_path.stem}_p{page_num}_c{chunk_idx}"
            documents.append(chunk)
            metadatas.append({
                "source": pdf_path.name,
                "page": page_num,
                "chunk": chunk_idx,
            })
            ids.append(doc_id)
    
    if not documents:
        return {"error": f"No chunks generated for {pdf_path.name}"}
    
    # Add to ChromaDB (will overwrite if IDs already exist)
    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    
    return {
        "file": pdf_path.name,
        "pages": len(pages),
        "chunks": len(documents),
    }


def index_all_pdfs(directory: Path = KNOWLEDGE_BASE_DIR) -> list[dict]:
    """Index every PDF inside the knowledge_base folder."""
    directory.mkdir(exist_ok=True)
    pdfs = list(directory.glob("*.pdf"))
    
    if not pdfs:
        return []
    
    results = []
    for pdf in pdfs:
        result = index_pdf(pdf)
        results.append(result)
    return results


# ─── Search ──────────────────────────────────────────────────
def search_knowledge_base(query: str, n_results: int = 3) -> dict:
    """
    Search the knowledge base semantically.
    
    Args:
        query: User question or search term
        n_results: How many top results to return
    
    Returns:
        dict with formatted snippets and sources
    """
    try:
        collection = get_collection()
        
        if collection.count() == 0:
            return {
                "results": [],
                "message": (
                    "Knowledge base is empty. Add PDFs to the 'knowledge_base/' "
                    "folder and re-index from the sidebar."
                ),
            }
        
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
        )
        
        snippets = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i] if results.get("distances") else None
            # Truncate each chunk to ~500 chars to save tokens
            text = doc.strip()
            if len(text) > 500:
                text = text[:500] + "..."
            snippets.append({
                "text": text,
                "source": meta.get("source", "unknown"),
                "page": meta.get("page", "?"),
                "relevance": round(1 - distance, 3) if distance is not None else None,
            })
        
        return {
            "query": query,
            "results": snippets,
            "count": len(snippets),
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}


# ─── Stats ───────────────────────────────────────────────────
def get_kb_stats() -> dict:
    """Get statistics about the knowledge base."""
    try:
        collection = get_collection()
        total_chunks = collection.count()
        
        # Get unique source files
        if total_chunks > 0:
            all_data = collection.get()
            sources = set(m.get("source", "unknown") for m in all_data["metadatas"])
        else:
            sources = set()
        
        return {
            "total_chunks": total_chunks,
            "total_sources": len(sources),
            "sources": sorted(sources),
        }
    except Exception as e:
        return {"error": str(e), "total_chunks": 0, "total_sources": 0, "sources": []}


def clear_knowledge_base():
    """Delete and recreate the collection (full reset)."""
    global _client, _collection
    
    if _client is None:
        get_collection()
    
    try:
        _client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    
    _collection = None
    get_collection()
    return {"status": "Knowledge base cleared"}


# ─── Quick Test ──────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing RAG module...\n")
    print(f"Stats: {get_kb_stats()}\n")
    print(f"Search test: {search_knowledge_base('inflation', n_results=2)}")