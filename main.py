from fastapi import FastAPI, Form, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os
from menus import pork_menus, beef_menus, ITEM_NAME_MAP
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

menu_items = {
    "돼지고기": [
        {"id": "p1", "name": "삼겹살", "price": 2967},
        {"id": "p2", "name": "오겹살", "price": 3134},
        {"id": "p3", "name": "목살", "price": 2634},
        {"id": "p4", "name": "앞다리살", "price": 1650},
        {"id": "p5", "name": "찌게용", "price": 1650},
        {"id": "p6", "name": "등갈비", "price": 2967},
        {"id": "p7", "name": "갈빗대벌집삼겹살", "price": 3300},
        {"id": "p8", "name": "생 대패삼겹살", "price": 2967},
        {"id": "p9", "name": "돈 등심", "price": 1650},
        {"id": "p10", "name": "돈 안심", "price": 1650},
        {"id": "p11", "name": "항정살", "price": 6500},
        {"id": "p12", "name": "가브리살(등심덧살)", "price": 5500},
        {"id": "p13", "name": "갈매기살", "price": 5000},
        {"id": "p14", "name": "꼬들살", "price": 3800},
        {"id": "p15", "name": "앞 사태(껍질o)", "price": 1967},
        {"id": "p16", "name": "돼지갈비", "price": 1650}
    ],
    "소고기 (특상한우 1++)": [
        {"id": "b1", "name": "한우 꽃등심", "price": 18800},
        {"id": "b2", "name": "한우 채끝등심", "price": 18000},
        {"id": "b3", "name": "한우 안심", "price": 18800},
        {"id": "b4", "name": "한우 치마살", "price": 21800},
        {"id": "b5", "name": "한우 살치살", "price": 21800},
        {"id": "b6", "name": "한우 꽃갈비살", "price": 21800},
        {"id": "b7", "name": "한우 부채살", "price": 18000},
        {"id": "b8", "name": "한우 업진살", "price": 18000},
        {"id": "b9", "name": "한우 갈비살", "price": 18000},
        {"id": "b10", "name": "한우 제비추리", "price": 18000},
        {"id": "b11", "name": "한우 안창살", "price": 29800},
        {"id": "b12", "name": "한우 토시살", "price": 21800},
        {"id": "b13", "name": "한우 양지 국거리", "price": 7500},
        {"id": "b14", "name": "한우 목심 양지", "price": 6000},
        {"id": "b15", "name": "한우 사태", "price": 5000},
        {"id": "b16", "name": "한우 우둔살", "price": 7000},
        {"id": "b17", "name": "한우 다짐육", "price": 7000},
        {"id": "b18", "name": "한우 육회", "price": 7500}
    ]
}

# === 공통 함수 ===

def load_orders():
    if not os.path.exists("orders.json"):
        return []
    with open("orders.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_orders(orders):
    with open("orders.json", "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

# === 페이지 라우팅 ===

@app.get("/", response_class=HTMLResponse)
async def order_page(request: Request):
    return templates.TemplateResponse("order.html", {
        "request": request,
        "menu_items": menu_items
    })

@app.get("/order-form", response_class=HTMLResponse)
async def order_form(request: Request):
    print(menu_items)
    return templates.TemplateResponse("order_form.html", {
        "request": request,
        "menu_items": menu_items  # menu_items를 템플릿에 넘겨줌
    })

@app.post("/order-form")
async def create_order_form(request: Request):
    form = await request.form()
    customer_name = form.get("customer_name")
    phone_number = form.get("phone_number")
    address = form.get("address")

    items = []
    for item_id, quantity in form.items():
        if item_id in ITEM_NAME_MAP:
            try:
                qty = int(quantity)
                if qty > 0:
                    items.append(f"{ITEM_NAME_MAP[item_id]} x {qty}")
            except ValueError:
                continue

    if not items:
        return templates.TemplateResponse("order_form.html", {
            "request": request,
            "menu_items": menu_items,
            "error": "상품을 하나 이상 선택해주세요."
        })

    order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order = {
        "time": order_time,
        "customer_name": customer_name,
        "phone_number": phone_number,
        "address": address,
        "items": items
    }

    orders = load_orders()
    orders.append(order)
    save_orders(orders)

    return RedirectResponse("/thanks", status_code=303)

@app.get("/thanks", response_class=HTMLResponse)
async def thank_you(request: Request):
    return templates.TemplateResponse("thanks.html", {"request": request})

@app.get("/orders", response_class=HTMLResponse)
async def read_orders(request: Request, q: Optional[str] = Query(None)):
    orders = load_orders()
    orders.sort(key=lambda x: x["time"], reverse=True)

    if q:
        orders = [
            o for o in orders
            if q in o["customer_name"]
            or q in o["address"]
            or any(q in item for item in o["items"])
        ]

    return templates.TemplateResponse("orders.html", {
        "request": request,
        "orders": orders,
        "query": q or ""
    })

@app.post("/delete-order")
async def delete_order(order_time: str = Form(...)):
    orders = load_orders()
    new_orders = [o for o in orders if o["time"] != order_time]
    save_orders(new_orders)
    return RedirectResponse(url="/orders", status_code=303)

# === 카카오 챗봇용 API ===

class KakaoOrder(BaseModel):
    customer_name: str
    phone_number: str
    address: str
    item: str
    quantity: int

@app.post("/order")
def create_kakao_order(order: KakaoOrder):
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
