from typing import List
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

class LocalMiniLMEmbeddings(Embeddings):
    """
    LangChain-compatible wrapper class for local SentenceTransformer model.
    Runs all-MiniLM-L6-v2 to compute 384-dimensional semantic vectors.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Load the sentence transformer model locally
        self.model = SentenceTransformer(model_name)
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of document strings.
        """
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
        
    def embed_query(self, text: str) -> List[float]:
        """
        Embeds a single search query string.
        """
        embedding = self.model.encode(text, show_progress_bar=False)
        return embedding.tolist()
