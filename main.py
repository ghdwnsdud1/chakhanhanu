from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

# 1. FastAPI 앱 생성
app = FastAPI()

# 2. 미들웨어 등록
app.add_middleware(SessionMiddleware, secret_key="supersecretkey123")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. 라우터 import 및 등록 (미들웨어 이후!)
from payment_routes import router as payment_router
from admin_routes import router as admin_router
from order_routes import router as order_router
from misc_routes import router as misc_router

app.include_router(payment_router)
app.include_router(admin_router)
app.include_router(order_router)
app.include_router(misc_router)

from datetime import datetime, timedelta
import asyncio
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["meatshop"]
orders_collection = db["orders"]

# ⭐ FastAPI 앱이 실행되면 자동으로 이 함수가 시작돼!
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(delete_old_orders())

# ⭐ 1시간마다 실행되는 함수
async def delete_old_orders():
    while True:
        three_days_ago = datetime.utcnow() - timedelta(days=3)

        # 문자열 → datetime 객체로 변환해서 비교해야 하므로 먼저 다 꺼내야 해
        orders = list(orders_collection.find())

        deleted_count = 0

        for order in orders:
            ts_str = order.get("timestamp")
            if ts_str:
                try:
                    ts_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    if ts_dt < three_days_ago:
                        orders_collection.delete_one({"_id": order["_id"]})
                        deleted_count += 1
                except Exception as e:
                    print(f"❌ 날짜 파싱 실패: {ts_str} → {e}")

        print(f"🧹 3일 지난 주문 {deleted_count}개 삭제 완료!")
        await asyncio.sleep(3600)
