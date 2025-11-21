from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import shutil
import os
import numpy as np
from db import users_collection, get_user, create_user
from ml_engine import voice_engine
from vector_db import vector_db
import mimetypes
import librosa
import soundfile as sf
import warnings

# Suppress specific librosa warning about PySoundFile
warnings.filterwarnings("ignore", message="PySoundFile failed. Trying audioread instead.")
warnings.filterwarnings("ignore", category=FutureWarning, module="librosa")

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = {'.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac', '.webm'}
SUPPORTED_MIME_TYPES = {
    'audio/wav', 'audio/mpeg', 'audio/ogg', 'audio/flac', 
    'audio/mp4', 'audio/aac', 'audio/x-wav', 'audio/x-m4a',
    'audio/webm', 'audio/x-matroska'
}

# Standard audio parameters for processing
TARGET_SAMPLE_RATE = 16000  # webrtcvad requires 16kHz

# 1. Lifespan: Load ML model on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load model and create folders
    os.makedirs("storage/audio", exist_ok=True)
    os.makedirs("storage/embeddings", exist_ok=True)
    voice_engine.load_model()
    yield
    # Shutdown: (Cleanup if needed)

app = FastAPI(lifespan=lifespan)

# Enable CORS for Frontend Access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"], # Allow Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER: Save Uploaded File ---
def save_file(file: UploadFile, destination_path: str):
    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

# --- HELPER: Validate Audio Format ---
def validate_audio_format(file: UploadFile) -> str:
    """Validate audio format and return the file extension."""
    filename = file.filename.lower()
    
    # Check file extension
    file_ext = os.path.splitext(filename)[1]
    if file_ext not in SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{file_ext}'. Supported formats: {', '.join(SUPPORTED_AUDIO_FORMATS)}"
        )
    
    # Check MIME type if available
    mime_type = file.content_type.lower() if file.content_type else ""
    if mime_type and mime_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audio MIME type '{mime_type}'. Please upload a valid audio file."
        )
    
    return file_ext

# --- HELPER: Validate Audio File ---
def validate_audio_file(file_path: str, min_size_bytes: int = 4096):
    """Check if audio file exists and has reasonable size."""
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Audio file was not saved properly.")
    
    file_size = os.path.getsize(file_path)
    if file_size < min_size_bytes:
        os.remove(file_path)  # Cleanup bad file
        raise HTTPException(
            status_code=400, 
            detail=f"Audio file too small ({file_size} bytes). Please upload a longer audio clip (at least 2+ seconds)."
        )

# --- HELPER: Convert Audio to Standard Format ---
def convert_audio_to_wav(input_path: str, output_path: str) -> None:
    """Convert any audio format to 16kHz mono WAV for compatibility."""
    try:
        # Load audio with librosa (handles most formats including webm)
        # Note: librosa uses ffmpeg or soundfile under the hood
        audio, sr = librosa.load(input_path, sr=TARGET_SAMPLE_RATE, mono=True)
        
        # Save as WAV
        sf.write(output_path, audio, TARGET_SAMPLE_RATE)
    except Exception as e:
        # Clean up if conversion fails
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process audio file: {str(e)}. Please ensure the audio file is valid."
        )

#--- API: Health Check ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}
@app.get("/")
async def root():
    return {"message": "Voice Verification API is running."}
# --- API: Register User ---
@app.post("/register")
async def register_user(
    user_id: str = Form(...), 
    file: UploadFile = File(...)
):
    # 1. Validate audio format
    file_ext = validate_audio_format(file)
    
    # 2. Check if user already exists
    existing_user = await get_user(user_id)
    if existing_user:
        raise HTTPException(status_code=400, detail="User ID already registered.")

    # 3. Define paths
    audio_path = f"storage/audio/{user_id}{file_ext}"
    # npy_path removed - using ChromaDB

    # 4. Save the Audio File locally
    try:
        save_file(file, audio_path)
        validate_audio_file(audio_path)  # Validate immediately after save
        
        # Always convert to standard WAV format (16kHz mono)
        # This handles webm, mp3, and even existing wav files to ensure correct sample rate
        wav_path = f"storage/audio/{user_id}.wav"
        convert_audio_to_wav(audio_path, wav_path)
        
        # If the original file was not .wav, remove it
        if audio_path != wav_path:
            os.remove(audio_path)
            
        # Update audio_path to point to the converted file
        audio_path = wav_path
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 4. Generate Voice ID (Embedding)
    # Note: get_embedding is CPU intensive. In heavy production, use background tasks.
    try:
        embedding = voice_engine.get_embedding(audio_path)
        # Store in ChromaDB instead of local .npy file
        vector_db.add_user_embedding(user_id, embedding)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Model Error: {str(e)}")

    # 5. Save to MongoDB (Metadata only)
    user_data = {
        "user_id": user_id,
        "audio_path": audio_path,
        "status": "active",
        "created_at": np.datetime64('now').astype(str)
    }
    await create_user(user_data)

    return {
        "message": "User registered successfully", 
        "user_id": user_id,
        "status": "Voice ID Created"
    }

# --- API: Verify User ---
@app.post("/verify")
async def verify_user(
    user_id: str = Form(...), 
    file: UploadFile = File(...)
):
    # 1. Validate audio format
    file_ext = validate_audio_format(file)
    print(user_id, file_ext)
    # 2. Check if user exists
    user_record = await get_user(user_id)
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found.")

    # 3. Save the temporary 'Verify' audio
    temp_verify_path = f"storage/audio/temp_{user_id}{file_ext}"
    
    try:
        save_file(file, temp_verify_path)
        validate_audio_file(temp_verify_path)
        
        # Always convert to standard WAV format (16kHz mono)
        wav_temp_path = f"storage/audio/temp_{user_id}.wav"
        convert_audio_to_wav(temp_verify_path, wav_temp_path)
        
        # If original was not wav, remove it
        if temp_verify_path != wav_temp_path:
            os.remove(temp_verify_path)
            
        # Update path to use the converted file
        temp_verify_path = wav_temp_path

        # 4. Load the Registered Embedding
        registered_embedding = vector_db.get_user_embedding(user_id)
        
        if registered_embedding is None:
             raise HTTPException(status_code=404, detail="Voice ID not found in database. Please register first.")

        # 5. Generate Embedding for New Audio
        new_embedding = voice_engine.get_embedding(temp_verify_path)

        # 6. Compare
        # Use stricter threshold (0.75) to prevent false positives
        match, score, threshold = voice_engine.verify(registered_embedding, new_embedding, threshold=0.75)

    finally:
        # Cleanup: Remove the temporary verify file
        if os.path.exists(temp_verify_path):
            os.remove(temp_verify_path)

    if match:
        return {
            "status": "success", 
            "message": "Voice Verified", 
            "score": score, 
            "threshold": threshold
        }
    else:
        raise HTTPException(
            status_code=401, 
            detail=f"Verification Failed. Score: {score:.4f} (Needed {threshold})"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)