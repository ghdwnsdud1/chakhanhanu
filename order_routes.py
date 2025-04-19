# order_routes.py
from fastapi import APIRouter, Request
from bson import ObjectId
from pydantic import BaseModel
from datetime import datetime
import pytz
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# MongoDB 연결
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["meatshop"]
orders_collection = db["orders"]

router = APIRouter()

# ✅ 주문 모델
class Order(BaseModel):
    items: list
    totalAmount: str
    contact: str
    name: str
    address: str
    doorcode: str
    requestMessage: str
    deliveryRequest: str
    paymentMethod: str
    depositorName: str = ""
    cashReceipt: str = ""

# ✅ 주문 저장
@router.post("/submit-order")
async def submit_order(order: Order):
    print("🔥 주문 들어옴")
    korea = pytz.timezone('Asia/Seoul')
    now_korea = datetime.now(korea).strftime("%Y-%m-%d %H:%M:%S")

    order_dict = order.dict()
    order_dict["timestamp"] = now_korea
    order_dict["is_paid"] = False

    result = orders_collection.insert_one(order_dict)

    return {"status": "success", "id": str(result.inserted_id)}

# ✅ 주문 목록 가져오기
@router.get("/get-orders")
async def get_orders():
    orders = list(orders_collection.find())
    for order in orders:
        order["_id"] = str(order["_id"])
    return orders

# ✅ 결제 완료 처리
@router.post("/mark-paid/{order_id}")
async def mark_paid(order_id: str):
    result = orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"is_paid": True}}
    )
    return {"message": "결제 완료 처리됨" if result.modified_count else "실패"}

# ✅ 주문 삭제
@router.post("/delete-order/{order_id}")
async def delete_order(order_id: str):
    result = orders_collection.delete_one({"_id": ObjectId(order_id)})
    return {"success": bool(result.deleted_count)}
