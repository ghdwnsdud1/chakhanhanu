from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
from datetime import datetime

app = FastAPI()

# 정적 파일 제공 (CSS, JS, 이미지)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 폴더 연결 (HTML 파일)
templates = Jinja2Templates(directory="templates")

# 주문 저장 파일
ORDER_FILE = "orders.json"

# 주문서 페이지 보여주기
@app.get("/", response_class=HTMLResponse)
async def order_form(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})

# 주문 제출 받기
@app.post("/submit", response_class=HTMLResponse)
async def submit_order(
    request: Request,
    name: str = Form(...),
    contact: str = Form(...),
    address: str = Form(...),
    doorcode: str = Form(...),
    payment_method: str = Form(...),
    request_message: str = Form(""),
    delivery_request: str = Form(""),
    depositor_name: str = Form(""),
    cash_receipt: str = Form(""),
    total_amount: str = Form(...),
    selected_items: str = Form(...)
):
    # 새 주문 데이터
    new_order = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": name,
        "contact": contact,
        "address": address,
        "doorcode": doorcode,
        "payment_method": payment_method,
        "depositor_name": depositor_name,
        "cash_receipt": cash_receipt,
        "request_message": request_message,
        "delivery_request": delivery_request,
        "total_amount": total_amount,
        "selected_items": json.loads(selected_items)
    }

    # 주문 파일 불러오기
    if os.path.exists(ORDER_FILE):
        with open(ORDER_FILE, "r", encoding="utf-8") as f:
            orders = json.load(f)
    else:
        orders = []

    orders.append(new_order)

    with open(ORDER_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

    return RedirectResponse(url="/success", status_code=303)

# 주문 성공 페이지
@app.get("/success", response_class=HTMLResponse)
async def success_page(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})
