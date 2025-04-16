from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient
from datetime import datetime
import pytz
from fastapi.responses import JSONResponse
import os

# ✅ 환경 변수 로딩
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# ✅ FastAPI 초기화
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ✅ CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 정적 파일 연결
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ MongoDB 연결
client = MongoClient(MONGO_URI)
db = client["meatshop"]
orders_collection = db["orders"]

# ✅ 주문 데이터 모델
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

# ✅ 주문 제출 (MongoDB에 저장)
@app.post("/submit-order")
async def submit_order(order: Order):
    print("🔥 주문 들어옴")
    order_dict = order.dict()
    korea = pytz.timezone('Asia/Seoul')
    now_korea = datetime.now(korea)
    order_dict["timestamp"] = now_korea.strftime("%Y-%m-%d %H:%M:%S")  # ✅ 문자열로 저장
    order_dict["is_paid"] = order.paymentMethod in ["card", "kakao"]
    result = orders_collection.insert_one(order_dict)
    return {"status": "success", "id": str(result.inserted_id)}

# ✅ 주문 목록 가져오기
@app.get("/get-orders")
async def get_orders():
    orders = list(orders_collection.find())
    for order in orders:
        order["_id"] = str(order["_id"])
        if isinstance(order.get("timestamp"), datetime):
            order["timestamp"] = order["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return jsonable_encoder(orders)

# ✅ 결제 완료 처리
@app.post("/mark-paid/{order_id}")
async def mark_paid(order_id: str):
    result = orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"is_paid": True}}
    )
    if result.modified_count:
        return {"message": "결제 완료 처리"}
    return {"error": "해당 주문을 찾을 수 없습니다"}

# ✅ 주문 삭제
@app.post("/delete-order/{order_id}")
async def delete_order(order_id: str):
    result = orders_collection.delete_one({"_id": ObjectId(order_id)})
    return {"success": bool(result.deleted_count)}

@app.get("/debug-orders")
async def debug_orders():
    orders = list(orders_collection.find())
    for order in orders:
        order["_id"] = str(order["_id"])  # ObjectId → 문자열 변환
        if isinstance(order.get("timestamp"), datetime):
            order["timestamp"] = order["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

    return JSONResponse(content={"count": len(orders), "sample": orders[-1] if orders else None})


# ✅ 템플릿 페이지들
@app.get("/", response_class=HTMLResponse)
async def order_form(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/success", response_class=HTMLResponse)
async def success_page(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})

@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})
