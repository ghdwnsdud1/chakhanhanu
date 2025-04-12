from fastapi import FastAPI, Form, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os
from menus import menu_items

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ====== 주문 데이터 관리 ======

def load_orders():
    if not os.path.exists("orders.json"):
        return []
    with open("orders.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_orders(orders):
    with open("orders.json", "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

# ====== 페이지 ======

@app.get("/", response_class=HTMLResponse)
async def home():
    return RedirectResponse(url="/orders")  # 첫 페이지를 주문서 목록으로 리디렉션

@app.get("/orders", response_class=HTMLResponse)
async def order_page(request: Request, q: Optional[str] = Query(None)):
    orders = load_orders()
    orders.sort(key=lambda x: x["time"], reverse=True)  # 최신순 정렬

    # 검색 필터
    if q:
        orders = [
            o for o in orders
            if q in o["customer_name"]
            or q in o["address"]
            or any(q in item for item in o.get("items", []))
        ]

    return templates.TemplateResponse("orders.html", {
"request": request,
 "orders": orders, 
"query": q or "",
"menu_items": menu_items
})

@app.get("/order-form", response_class=HTMLResponse)
async def order_form(request: Request):
    return templates.TemplateResponse("orders.html", {"request": request})

@app.post("/order-form")
async def create_order(
    customer_name: str = Form(...),
    phone_number: Optional[str] = Form(None),
    address: str = Form(...),
    item: Optional[str] = Form(None),
    quantity: Optional[int] = Form(0),
):
    order = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": customer_name,
        "phone_number": phone_number,
        "address": address,
        "items": [{"name": item, "quantity": quantity}] if item else []
    }

    orders = load_orders()
    orders.append(order)
    save_orders(orders)

    return RedirectResponse(url="/orders", status_code=303)

@app.post("/delete-order")
async def delete_order(order_time: str = Form(...)):
    orders = load_orders()
    orders = [o for o in orders if o["time"] != order_time]
    save_orders(orders)
    return RedirectResponse(url="/orders", status_code=303)

# ====== 카카오 챗봇용 API ======

class KakaoOrder(BaseModel):
    customer_name: str
    phone_number: str
    address: str
    item: str
    quantity: int

@app.post("/order")
async def create_kakao_order(order: KakaoOrder):
    order_data = order.dict()
    order_data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    orders = load_orders()
    orders.append(order_data)
    save_orders(orders)

    return JSONResponse(content={
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "주문이 접수되었습니다. 감사합니다! 😊"
                    }
                }
            ]
        }
    })
