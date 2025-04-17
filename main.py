from fastapi import FastAPI, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
import pytz, os

# ✅ 기본 설정
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey123")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["meatshop"]
orders_collection = db["orders"]

# ✅ 관리자 계정
ADMIN_ID = "ghdwnsdud1"
ADMIN_PW = "0214"

# ✅ 로그인 페이지
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# ✅ 로그인 처리
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), request: Request = None):
    if username == ADMIN_ID and password == ADMIN_PW:
        request.session["logged_in"] = True
        return RedirectResponse(url="/admin", status_code=302)
    return HTMLResponse(content="❌ 로그인 실패", status_code=401)

# ✅ 로그아웃 처리
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

# ✅ 관리자 페이지 (로그인 체크 포함)
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    return templates.TemplateResponse("admin.html", {"request": request})

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
@app.post("/submit-order")
async def submit_order(order: Order):
    print("🔥 주문 들어옴")
    korea = pytz.timezone('Asia/Seoul')
    now_korea = datetime.now(korea).strftime("%Y-%m-%d %H:%M:%S")
    order_dict = order.dict()
    order_dict["timestamp"] = now_korea
    order_dict["is_paid"] = order.paymentMethod in ["card", "kakao"]
    result = orders_collection.insert_one(order_dict)
    return {"status": "success", "id": str(result.inserted_id)}

# ✅ 주문 목록
@app.get("/get-orders")
async def get_orders():
    orders = list(orders_collection.find())
    for order in orders:
        order["_id"] = str(order["_id"])
    return orders

# ✅ 결제 완료 처리
@app.post("/mark-paid/{order_id}")
async def mark_paid(order_id: str):
    result = orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"is_paid": True}}
    )
    return {"message": "결제 완료 처리됨" if result.modified_count else "실패"}

# ✅ 주문 삭제
@app.post("/delete-order/{order_id}")
async def delete_order(order_id: str):
    result = orders_collection.delete_one({"_id": ObjectId(order_id)})
    return {"success": bool(result.deleted_count)}

# ✅ 기타 템플릿
@app.get("/", response_class=HTMLResponse)
async def order_form(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})

@app.get("/success", response_class=HTMLResponse)
async def success(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})

@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})
