from datetime import datetime, timedelta
import asyncio
import json
import os

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
load_dotenv()

from db import orders_collection
from payment_routes import router as payment_router
from admin_routes import router as admin_router
from order_routes import router as order_router
from misc_routes import router as misc_router

# FastAPI 앱 생성
app = FastAPI()

# 세션 미들웨어 (6시간 유효)
app.add_middleware(SessionMiddleware, secret_key="your_secret_key_here", max_age=6*60*60)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일, 템플릿 경로
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 라우터 등록
app.include_router(payment_router)
app.include_router(admin_router)
app.include_router(order_router)
app.include_router(misc_router)

# 헬스체크
@app.get("/")
def keep_alive():
    return {"status": "ok"}

@app.head("/")
def head_alive():
    return

# 자동 삭제: 7일 지난 주문
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(delete_old_orders())

async def delete_old_orders():
    while True:
        three_days_ago = datetime.utcnow() - timedelta(days=7)
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

# 로그인 인증 검사
def get_current_user(request: Request):
    return request.session.get("logged_in")

# 로그인 페이지
@app.get("/admin/login", response_class=HTMLResponse)
async def show_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 로그인 처리
@app.post("/admin/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    if username == "admin" and password == "password":
        request.session["logged_in"] = True
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return HTMLResponse("로그인 실패", status_code=401)

# 로그아웃
@app.get("/admin/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login")

# 관리자 대시보드
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    return templates.TemplateResponse("dashboard.html", {"request": request})
# 상품 관리 페이지
@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request):
    if request.headers.get("referer", "").endswith("/dashboard"):
        return templates.TemplateResponse("admin_products.html", {"request": request})
    return RedirectResponse(url="/dashboard")

# 상품 리스트 (가상)
products = [
    {"name": "한우 등심", "price": 29800, "status": "판매중"},
    {"name": "돼지 목살", "price": 13800, "status": "품절"},
]

@app.get("/get-products")
async def get_products():
    return JSONResponse(content=products)

@app.post("/update-product")
async def update_product(request: Request):
    data = await request.json()
    index = data.get("index")
    name = data.get("name")
    price = data.get("price")
    status = data.get("status")

    if index is None:
        return JSONResponse(content={"message": "index 없음"}, status_code=400)

    update_sheet_row(index, name, price, status)

    return JSONResponse(content={"message": "상품이 수정되었습니다."})


def update_sheet_row(index, name, price, status):
    try:
        key_path = os.getenv("GOOGLE_SHEETS_KEY_PATH")
        if not key_path or not os.path.exists(key_path):
            print("❌ 키 파일을 찾을 수 없습니다.")
            return
        print("🔐 키 파일 경로:", key_path)

        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scope)
        client = gspread.authorize(creds)

        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1ZdFmBrhvHmJ3wpYrlnWSm1WvZAw3ac6Qg9JuBEvSpwI")
        worksheet = sheet.get_worksheet(0)

        row = index + 2
        worksheet.update_cell(row, 1, name)
        worksheet.update_cell(row, 3, price)
        worksheet.update_cell(row, 4, status)

        print("✅ 시트 업데이트 성공!")

    except Exception as e:
        print("❌ 시트 업데이트 오류:", e)

key_path = os.getenv("GOOGLE_SHEETS_KEY_PATH")

if not key_path or not os.path.exists(key_path):
    print("❌ 키 파일을 찾을 수 없습니다.")
else:
    print("🔐 키 파일 경로:", key_path)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scope)
    print("✅ 시트 인증 객체 생성 성공!")

@app.post("/submit-order")
async def submit_order(request: Request):
    data = await request.json()
    # 주문 MongoDB 저장 처리...
    return {"success": True}