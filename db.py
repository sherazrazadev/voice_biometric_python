from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
load_dotenv()
# MongoDB URL (default local)
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "voice_auth_db")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
users_collection = db["registered_users"]

async def get_user(user_id: str):
    return await users_collection.find_one({"user_id": user_id})

async def create_user(user_data: dict):
    return await users_collection.insert_one(user_data)