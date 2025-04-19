from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import pytz, os, io
import pandas as pd

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
def determine_delivery_date(timestamp_str, tz):
    try:
        order_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        # 이미 timezone이 들어있는 datetime이면 localize하면 안됨!
        if order_time.tzinfo is None:
            order_time = tz.localize(order_time)
        else:
            order_time = order_time.astimezone(tz)

        cutoff = order_time.replace(hour=14, minute=0, second=0, microsecond=0)
        delivery_date = (order_time + timedelta(days=1)).date() if order_time > cutoff else order_time.date()
        return str(delivery_date)
    except Exception as e:
        print("❌ 배송일자 분류 실패:", e)
        return "분류불가"

# ✅ 주문 목록 반환 (관리자 페이지용)
@router.get("/get-orders")
async def get_orders():
    orders = list(orders_collection.find())
    korea = pytz.timezone('Asia/Seoul')
    for order in orders:
        order["_id"] = str(order["_id"])
        order["배송일자"] = determine_delivery_date(order.get("timestamp", ""), korea)
    return orders
# ✅ 엑셀 다운로드
@router.get("/download-orders")
async def download_orders():
    orders = list(orders_collection.find())
    korea = pytz.timezone('Asia/Seoul')

    for order in orders:
        order["_id"] = str(order["_id"])
        order["배송일자"] = determine_delivery_date(order.get("timestamp", ""), korea)

    df = pd.DataFrame(orders)
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=orders.xlsx"}
    )
