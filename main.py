from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials

# 1. FastAPI 앱 생성
app = FastAPI()

# 2. 미들웨어 등록
app.add_middleware(SessionMiddleware, secret_key="supersecretkey123")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계에서는 * 사용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
from db import orders_collection

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ⭐ FastAPI 앱이 실행되면 자동으로 이 함수가 시작돼!
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(delete_old_orders())

@app.get("/")
def keep_alive():
    return {"status": "ok"}

@app.head("/")
def head_alive():
    return
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

@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products_page(request: Request):
    return templates.TemplateResponse("admin_products.html", {"request": request})

# 임시 상품 리스트 (Google Sheets 대신)
products = [
    {"name": "한우 등심", "price": 29800, "status": "판매중"},
    {"name": "돼지 목살", "price": 13800, "status": "품절"},
]

# 상품 리스트를 반환하는 API
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

    if index is not None and 0 <= index < len(products):
        products[index] = {
            "name": name,
            "price": price,
            "status": status
        }

        update_sheet_row(index, name, price, status)

        return JSONResponse(content={"message": "상품이 수정되었습니다."})
    else:
        return JSONResponse(content={"message": "상품 수정 실패: index 오류"}, status_code=400)

# 시트 연동 준비
def update_sheet_row(index, name, price, status):
    try:
        # ✅ 환경변수 대신 Secret File 경로에서 읽기
        with open("/etc/secrets/GOOGLE_SHEETS_KEY") as f:
            json_key = f.read()
        if not json_key:
            print("❌ 환경변수 GOOGLE_SHEETS_KEY 를 못 불러왔어요!")
            return  # 더 이상 진행하면 안 되니까 종료

        print("🔐 환경변수 불러오기 성공!")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Render 환경변수에서 JSON 텍스트 불러오기
        json_str = os.getenv("GOOGLE_SHEETS_KEY")
        creds_dict = json.loads(json_str)

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1ZdFmBrhvHmJ3wpYrlnWSm1WvZAw3ac6Qg9JuBEvSpwI")
        worksheet = sheet.get_worksheet(0)

        row = index + 2
        worksheet.update_cell(row, 1, name)
        worksheet.update_cell(row, 3, price)
        worksheet.update_cell(row, 4, status)

    except Exception as e:
        print("❌ 시트 업데이트 중 오류:", e)