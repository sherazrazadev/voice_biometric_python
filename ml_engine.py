from verifyvoice import ModelLoader
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class VoiceModelEngine:
    def __init__(self):
        self.model = None

    def load_model(self):
        """Loads the WavLM model into memory."""
        print("🤖 Loading Voice AI Model... (This may take a few seconds)")
        self.model = ModelLoader(model_name="WavLM", attention_heads=8)
        print("✅ Model Loaded Successfully.")

    def get_embedding(self, audio_path: str):
        """Generates the math vector for a voice file."""
        if not self.model:
            raise ValueError("Model not loaded!")
        
        # Get embedding from model
        embedding = self.model.get_embedding(audio_path)
        
        # Ensure it's a numpy array and flattened
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        return embedding.flatten()

    def verify(self, registered_embedding, verify_embedding, threshold: float = 0.65):
        """
        Compares two voice embeddings.
        
        Args:
            registered_embedding: The stored embedding of the user.
            verify_embedding: The new embedding to verify.
            threshold: The score required to pass verification (0.0 to 1.0).
                      Default raised to 0.75 for stricter security.
        """
        # Reshape for sklearn (1, -1) means 1 row, unknown columns
        reg_emb = registered_embedding.reshape(1, -1)
        ver_emb = verify_embedding.reshape(1, -1)
        
        # Calculate Cosine Similarity (-1 to 1)
        score = cosine_similarity(reg_emb, ver_emb)[0][0]
        
        # Determine match based on strict threshold
        is_match = bool(score >= threshold)
        
        return is_match, float(score), float(threshold)

# Create a global instance
voice_engine = VoiceModelEngine()