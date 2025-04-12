from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER
import json
import uuid
import os
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

status_flow = ["결제 요청됨", "결제 완료됨", "배송 중", "배송 완료"]
orders_file = "orders.json"

def load_orders():
    if not os.path.exists(orders_file):
        return []
    with open(orders_file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_orders(orders):
    with open(orders_file, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

# 🏠 홈 → 주문서 폼
@app.get("/", response_class=HTMLResponse)
async def order_form(request: Request):
    return templates.TemplateResponse("order_form.html", {"request": request})

# ✅ 주문 저장
@app.post("/submit")
async def submit_order(
    request: Request,
    customer_name: str = Form(...),
    phone_number: str = Form(...),
    address: str = Form(...),
    item_samgyeop: int = Form(...),
    item_moksal: int = Form(...),
    item_galbi: int = Form(...)
):
    orders = load_orders()
    new_order = {
        "id": str(uuid.uuid4()),
        "name": customer_name,
        "address": address,
        "phone": phone_number,
        "items": {
            "삼겹살": item_samgyeop,
            "목살": item_moksal,
            "앞다리살": item_galbi
        },
        "status": status_flow[0],
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    orders.append(new_order)
    save_orders(orders)
    return RedirectResponse(url="/done", status_code=HTTP_303_SEE_OTHER)

# ✅ 주문 완료 안내
@app.get("/done", response_class=HTMLResponse)
async def done(request: Request):
    return templates.TemplateResponse("done.html", {"request": request})

# ✅ 관리자 페이지 (주문 목록)
@app.get("/orders", response_class=HTMLResponse)
async def order_list(request: Request):
    orders = load_orders()
    sorted_orders = sorted(orders, key=lambda x: x["time"], reverse=True)
    return templates.TemplateResponse("orders.html", {"request": request, "orders": sorted_orders})
