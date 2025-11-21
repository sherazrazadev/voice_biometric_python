import chromadb
import numpy as np
import os

class VectorDB:
    def __init__(self, persist_directory="storage/chroma_db"):
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize Persistent Client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Create or get collection
        # Using cosine distance for similarity search
        self.collection = self.client.get_or_create_collection(
            name="voice_embeddings",
            metadata={"hnsw:space": "cosine"} 
        )

    def add_user_embedding(self, user_id: str, embedding: np.ndarray):
        """
        Stores a user's voice embedding.
        Overwrites if user_id already exists.
        """
        # Ensure embedding is a flat list
        embedding_list = embedding.flatten().tolist()
        
        # Upsert (Update or Insert)
        self.collection.upsert(
            ids=[user_id],
            embeddings=[embedding_list],
            metadatas=[{"user_id": user_id}],
            documents=[f"Voice embedding for user {user_id}"]
        )

    def get_user_embedding(self, user_id: str):
        """Retrieves a user's embedding as a numpy array."""
        result = self.collection.get(
            ids=[user_id],
            include=["embeddings"]
        )
        
        # Check if embeddings list is not empty
        # Explicitly check if the list is not None and has elements
        embeddings = result.get("embeddings")
        if embeddings is not None and len(embeddings) > 0:
            return np.array(embeddings[0])
        return None
    
    def delete_user(self, user_id: str):
        """Removes a user from the vector database."""
        self.collection.delete(ids=[user_id])

# Global instance
vector_db = VectorDB()
