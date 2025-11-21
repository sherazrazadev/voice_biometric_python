from motor.motor_asyncio import AsyncIOMotorClient
import os

# MongoDB URL (default local)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "voice_auth_db"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
users_collection = db["registered_users"]

async def get_user(user_id: str):
    return await users_collection.find_one({"user_id": user_id})

async def create_user(user_data: dict):
    return await users_collection.insert_one(user_data)