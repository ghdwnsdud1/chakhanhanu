from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import pytz, os, io
import pandas as pd
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from bson import ObjectId
from db import orders_collection
from pydantic import BaseModel
from typing import List, Optional

# ✅ 주문 데이터 모델
class Item(BaseModel):
    meat: str
    weight: int
    pricePerUnit: int
    type: str

class Order(BaseModel):
    items: List[Item]
    totalAmount: str
    contact: str
    name: str
    address: str
    doorcode: Optional[str] = ''
    requestMessage: Optional[str] = ''
    deliveryRequest: Optional[str] = ''
    paymentMethod: str  # 🔥 이거 중요 (추가)
    depositorName: Optional[str] = ''
    cashReceipt: Optional[str] = ''
    imp_uid: Optional[str] = ''
    isPaid: bool

# ✅ DB 연결
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["meatshop"]
orders_collection = db["orders"]

# ✅ 템플릿 설정
templates = Jinja2Templates(directory="templates")

# ✅ 라우터 정의
router = APIRouter()

# ✅ 관리자 계정 정보
ADMIN_ID = "ghdwnsdud1"
ADMIN_PW = "0214"

# ✅ 로그인 페이지
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# ✅ 로그인 처리
@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...), request: Request = None):
    if username == ADMIN_ID and password == ADMIN_PW:
        request.session["logged_in"] = True
        return RedirectResponse(url="/admin", status_code=302)
    return HTMLResponse(content="❌ 로그인 실패", status_code=401)

# ✅ 로그아웃 처리
@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

# ✅ 관리자 페이지
@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    return templates.TemplateResponse("admin.html", {"request": request})

# ✅ 배송일자 분류 함수 (오후 2시 기준)
def determine_delivery_date(timestamp_str):
    try:
        korea = pytz.timezone('Asia/Seoul')
        order_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        order_time = korea.localize(order_time)  # 한국 시간대 적용

        cutoff = order_time.replace(hour=14, minute=0, second=0, microsecond=0)

        if order_time <= cutoff:
            delivery_date = order_time.date()
        else:
            delivery_date = (order_time + timedelta(days=1)).date()

        return str(delivery_date)
    except Exception as e:
        print(f"배송일자 계산 실패: {e}")
        return "분류불가"


# ✅ 주문 목록 반환 (관리자 페이지용)
@router.get("/get-orders")
async def get_orders():
    orders = []
    for order in orders_collection.find({}).sort("timestamp", -1):
        order["_id"] = str(order["_id"])

        # ✅ 여기 추가
        order["isPaid"] = order.get("isPaid", False)

        # ✅ 배송일자 자동 계산 추가
        ts = order.get("timestamp")
        if ts:
            order["배송일자"] = determine_delivery_date(ts)
        else:
            order["배송일자"] = "분류불가"

        orders.append(order)
    return JSONResponse(content=orders)

# ✅ 결제 완료 처리
@router.post("/mark-paid/{order_id}")
async def mark_paid(order_id: str):
    try:
        result = orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"isPaid": True,}} 
        )
        if result.modified_count == 1:
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Order not found")
    except Exception as e:
        print(f"❌ 결제완료 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail="Server error")

# ✅ 엑셀 다운로드
@router.get("/download-orders")
async def download_orders():
    orders = list(orders_collection.find())
    korea = pytz.timezone('Asia/Seoul')

    for order in orders:
        order["_id"] = str(order["_id"])
        order["배송일자"] = determine_delivery_date(order.get("timestamp", ""), korea)

    df = pd.DataFrame([{
        "이름": order.get("name", "-"),
        "연락처": order.get("contact", "-"),
        "주문상품": ', '.join([
            f"{item['meat']} {item['weight']}{'g' if item['type'] != 'marinated' else '개'}"
            for item in order.get("items", [])
        ]),
        "결제상태": "완료" if order.get("isPaid", False) else "미완료",
        "요청사항": order.get("requestMessage", "-"),
    } for order in orders]),

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='주문내역')
        worksheet = writer.sheets['주문내역']

        bold_font = Font(name='맑은 고딕', size=13)
        wrap_text_align = Alignment(wrap_text=True, vertical='top')

        for idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=worksheet.max_row, min_col=1, max_col=worksheet.max_column), start=1):
            for cell in row:
                cell.font = bold_font
                cell.alignment = wrap_text_align

        column_widths = {
            'A': 14,
            'B': 20,
            'C': 50,
            'D': 12,
            'E': 50
        }
        for col_letter, width in column_widths.items():
            worksheet.column_dimensions[col_letter].width = width

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=chakhanhanu_orders.xlsx"}
    )
