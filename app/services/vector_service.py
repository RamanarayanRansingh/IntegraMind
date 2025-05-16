import os
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import json

import fitz  # PyMuPDF
from chromadb import PersistentClient
from chromadb.api.types import EmbeddingFunction
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ——— Logging Setup ——————————————————————————————————————————————
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("vector_service")

# ——— Embedding Function ——————————————————————————————————————————
class MentalHealthEmbedding(EmbeddingFunction):
    """Domain‑tuned embedding fn using SBERT mpnet for mental‑health text."""
    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        self.model = SentenceTransformer(model_name, device="cpu")

    def __call__(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, show_progress_bar=False).tolist()

# ——— Main Vector Store Class ——————————————————————————————————————
class MentalHealthVectorStore:
    def __init__(
        self,
        db_path: str = "data/chroma_db",
        kb_path: str = "knowledge_base",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        index_record_file: str = "data/indexed_files.json"
    ):
        self.db_path = db_path
        self.kb_path = kb_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.index_record_file = index_record_file
        self.indexed_files = self._load_indexed_files()

        # Create necessary directories
        os.makedirs(self.db_path, exist_ok=True)
        os.makedirs(self.kb_path, exist_ok=True)
        os.makedirs(os.path.dirname(self.index_record_file), exist_ok=True)

        # init ChromaDB + collections
        self.client = PersistentClient(path=self.db_path)
        logger.info(f"ChromaDB client initialized at {self.db_path}")
        self.embedding_fn = MentalHealthEmbedding()
        self.collections = self._create_collections()

        self._check_collections()

    def _load_indexed_files(self) -> Dict[str, datetime]:
        """Load record of previously indexed files with timestamps."""
        if os.path.exists(self.index_record_file):
            try:
                with open(self.index_record_file, 'r') as f:
                    data = json.load(f)
                # Convert string dates back to datetime objects
                return {k: datetime.fromisoformat(v) for k, v in data.items()}
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading indexed files record: {e}")
                return {}
        return {}

    def _save_indexed_files(self):
        """Save the record of indexed files to disk."""
        try:
            # Convert datetime objects to ISO format strings for JSON serialization
            serializable_data = {k: v.isoformat() for k, v in self.indexed_files.items()}
            with open(self.index_record_file, 'w') as f:
                json.dump(serializable_data, f)
            logger.debug(f"Saved indexed files record to {self.index_record_file}")
        except IOError as e:
            logger.error(f"Error saving indexed files record: {e}")

    def _create_collections(self) -> Dict[str, any]:
        folder_map = {
            "CBT Exercises and Worksheets": "cbt_resources",
            "Crisis Protocols and Safety Planning": "crisis_protocols",
            "Psychoeducational Materials": "psychoeducation",
            "Evidence-Based Intervention Guides": "interventions",
        }
        meta = {
            "cbt_resources": {"description": "CBT exercises & worksheets"},
            "psychoeducation": {"description": "Psychoeducational materials"},
            "crisis_protocols": {"description": "Crisis protocols & safety planning"},
            "interventions": {"description": "Evidence-based intervention guides"},
        }
        cols = {}
        for name in meta:
            cols[name] = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_fn,
                metadata=meta[name]
            )
        self.folder_map = folder_map
        return cols

    def _check_collections(self):
        for name, col in self.collections.items():
            count = col.count()
            logger.info(f"Collection '{name}': {count} chunks")
            if count == 0:
                logger.warning(f" → '{name}' is empty. Needs indexing.")

    def _determine_type(self, filepath: str) -> str:
        rel = os.path.relpath(filepath, self.kb_path)
        folder = rel.split(os.sep)[0]
        return self.folder_map.get(folder, "interventions")

    def process_pdf(self, filepath: str) -> List[Dict]:
        """
        Opens a PDF, extracts text page by page, splits into overlapping
        chunks, and returns a list of { id, text, metadata }.
        """
        logger.info(f"Processing PDF: {filepath}")
        chunks = []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        try:
            doc = fitz.open(filepath)
            total_pages = doc.page_count
            for pg_idx, page in enumerate(doc.pages(), start=1):
                text = page.get_text("text")
                if not text.strip():
                    logger.debug(f"Page {pg_idx} empty; skipping.")
                    continue
                pieces = splitter.split_text(text)
                for i, piece in enumerate(pieces, start=1):
                    chunk_id = f"{os.path.basename(filepath)}_p{pg_idx}_c{i}"
                    metadata = {
                        "source": os.path.basename(filepath),
                        "page": pg_idx,
                        "pages": f"{pg_idx}",
                        "total_pages": total_pages,
                        "indexed_date": datetime.utcnow().isoformat(),
                        "document_type": self._determine_type(filepath)
                    }
                    chunks.append({"id": chunk_id, "text": piece, "metadata": metadata})
            logger.info(f" → Created {len(chunks)} chunks from {filepath}")
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
        return chunks

    def check_file_modified(self, filepath: str) -> bool:
        """Check if a file has been modified since last indexing."""
        if filepath not in self.indexed_files:
            return True
        
        last_indexed = self.indexed_files.get(filepath)
        last_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        # If the file has been modified since last indexing, we need to re-index
        return last_modified > last_indexed

    def index_knowledge_base(self, force: bool = False) -> Tuple[int, int]:
        """
        Walks the KB dir, processes new/modified PDFs, and adds chunks to ChromaDB.
        Returns (files_processed, chunks_added).
        """
        files_processed = 0
        chunks_added = 0
        files_to_process = []

        # First, gather all files that need processing
        for root, _, files in os.walk(self.kb_path):
            for fn in files:
                if fn.lower().endswith(".pdf"):
                    path = os.path.join(root, fn)
                    if force or self.check_file_modified(path):
                        files_to_process.append(path)
        
        if not files_to_process:
            logger.info("No new or modified files to index.")
            return 0, 0
        
        # Process each file that needs indexing
        for path in files_to_process:
            doc_type = self._determine_type(path)
            collection = self.collections[doc_type]
            
            # If we're re-indexing, first remove existing chunks for this file
            if path in self.indexed_files:
                basename = os.path.basename(path)
                existing_ids = []
                
                # Find all chunks from this file
                results = collection.get(
                    where={"source": basename}
                )
                
                if results and "ids" in results and results["ids"]:
                    existing_ids = results["ids"]
                
                if existing_ids:
                    logger.info(f"Removing {len(existing_ids)} existing chunks for {basename}")
                    collection.delete(ids=existing_ids)
            
            # Now process and add new chunks
            chunks = self.process_pdf(path)
            if chunks:
                files_processed += 1
                
                # Add chunks in batches to improve performance
                batch_size = 100
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i+batch_size]
                    collection.add(
                        ids=[c["id"] for c in batch],
                        documents=[c["text"] for c in batch],
                        metadatas=[c["metadata"] for c in batch]
                    )
                
                chunks_added += len(chunks)
                # Record that we've indexed this file
                self.indexed_files[path] = datetime.now()
        
        # Save the record of indexed files
        self._save_indexed_files()
        
        logger.info(f"Indexed KB: {files_processed} files → {chunks_added} chunks")
        self._check_collections()
        return files_processed, chunks_added

    def query(
        self,
        text: str,
        categories: Optional[List[str]] = None,
        n_results: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Semantic search across one or all collections.
        """
        cols = (
            [self.collections[c] for c in categories if c in self.collections]
            if categories else
            list(self.collections.values())
        )
        out = {}
        for col in cols:
            if col.count() == 0:
                out[col.name] = []
                continue
            res = col.query(query_texts=[text], n_results=n_results)
            docs = []
            for doc, meta, did, dist in zip(
                res["documents"][0],
                res["metadatas"][0],
                res["ids"][0],
                res["distances"][0]
            ):
                docs.append({
                    "id": did,
                    "content": doc,
                    "metadata": meta,
                    "score": dist
                })
            out[col.name] = docs
        return out

    def get_document_by_id(self, collection: str, doc_id: str) -> Optional[Dict]:
        col = self.collections.get(collection)
        if not col:
            logger.warning(f"Unknown collection '{collection}'")
            return None
        res = col.get(ids=[doc_id])
        if res["documents"] and res["documents"][0]:
            return {
                "content": res["documents"][0],
                "metadata": res["metadatas"][0]
            }
        return None

    def search_by_category(
        self, query: str, category: str, n_results: int = 3
    ) -> List[Dict]:
        return self.query(query, categories=[category], n_results=n_results).get(category, [])

# ——— Singleton & Initialization ——————————————————————————————————————
mental_health_vector_store = MentalHealthVectorStore()

def init_vector_store():
    """Run once at startup (if not __main__) to index KB."""
    fp, ca = mental_health_vector_store.index_knowledge_base()
    if fp == 0 and ca == 0:
        # Only show warning if collections are empty
        if any(col.count() == 0 for col in mental_health_vector_store.collections.values()):
            logger.warning("No chunks added; verify KB folder structure.")
        else:
            logger.info("All files already indexed; no re-indexing needed.")

# Only auto‑index if imported, not when executed as script
if __name__ != "__main__":
    init_vector_store()
else:
    # When run as a script, just print collection stats
    for name, col in mental_health_vector_store.collections.items():
        count = col.count()
        logger.info(f"Collection '{name}': {count} chunks")