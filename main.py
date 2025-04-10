from fastapi import FastAPI, Form, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 주문 폼 페이지
@app.get("/order-form", response_class=HTMLResponse)
async def order_form(request: Request):
    return templates.TemplateResponse("order_form.html", {"request": request})

# 주문 저장
@app.post("/order-form")
async def create_order_form(
    customer_name: str = Form(...),
    phone_number: Optional[str] = Form(None),
    address: str = Form(...),
    item_samgyeop: int = Form(0),
    item_moksal: int = Form(0),
    item_galbi: int = Form(0),
):
    order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items = []
    if item_samgyeop > 0:
        items.append(f"삼겹살 x {item_samgyeop}")
    if item_moksal > 0:
        items.append(f"목살 x {item_moksal}")
    if item_galbi > 0:
        items.append(f"갈비 x {item_galbi}")

    if not items:
        return {"message": "상품을 하나 이상 선택해주세요."}

    order = {
        "time": order_time,
        "customer_name": customer_name,
        "phone_number": phone_number,
        "address": address,
        "items": items
    }

    # JSON 파일에 저장
    if not os.path.exists("orders.json"):
        with open("orders.json", "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

    with open("orders.json", "r+", encoding="utf-8") as f:
        data = json.load(f)
        data.append(order)
        f.seek(0)
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "message": "주문이 저장되었습니다!",
        "order": order
    }

# 주문 목록 페이지
@app.get("/orders", response_class=HTMLResponse)
async def read_orders(request: Request, q: Optional[str] = Query(None)):
    orders = []
    try:
        with open("orders.json", "r", encoding="utf-8") as f:
            orders = json.load(f)
    except FileNotFoundError:
        pass

    # 최신순 정렬
    orders.sort(key=lambda x: x["time"], reverse=True)

    # 검색 필터링
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

# 주문 삭제
@app.post("/delete-order")
async def delete_order(order_time: str = Form(...)):
    try:
        with open("orders.json", "r", encoding="utf-8") as f:
            orders = json.load(f)
        new_orders = [o for o in orders if o["time"] != order_time]
        with open("orders.json", "w", encoding="utf-8") as f:
            json.dump(new_orders, f, ensure_ascii=False, indent=2)
    except FileNotFoundError:
        pass

    return RedirectResponse(url="/orders", status_code=303)

# 카카오 챗봇용 주문 모델
class KakaoOrder(BaseModel):
    customer_name: str
    phone_number: str
    address: str
    item: str
    quantity: int

# 카카오 챗봇 연동
@app.post("/order")
def create_kakao_order(order: KakaoOrder):
    order_data = order.dict()
    order_data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not os.path.exists("orders.json"):
        with open("orders.json", "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

    with open("orders.json", "r+", encoding="utf-8") as f:
        data = json.load(f)
        data.append(order_data)
        f.seek(0)
        json.dump(data, f, ensure_ascii=False, indent=2)

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

# 첫 페이지는 주문 폼으로 리디렉트
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return RedirectResponse(url="/order-form")
