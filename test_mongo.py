from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

# .env 파일에서 MONGO_URI 불러오기
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")

print("✅ .env에서 불러온 URI:", mongo_uri)

try:
    # MongoDB 클라이언트 생성
    client = MongoClient(mongo_uri, server_api=ServerApi('1'))

    # 연결 확인용 ping
    client.admin.command('ping')
    print("✅ MongoDB 연결 성공!")

except Exception as e:
    print("❌ MongoDB 연결 실패:", e)
