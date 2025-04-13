from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 주문 저장할 파일
ORDER_FILE = "orders.json"

# 파일에서 주문 데이터 로드
if os.path.exists(ORDER_FILE):
    with open(ORDER_FILE, "r", encoding="utf-8") as f:
        orders = json.load(f)
else:
    orders = []

# 주문서 페이지
@app.get("/", response_class=HTMLResponse)
async def order_form(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})

# 주문 성공 페이지
@app.get("/success", response_class=HTMLResponse)
async def success_page(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

# 관리자 페이지
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

# 주문 제출
@app.post("/submit-order")
async def submit_order(request: Request):
    data = await request.json()
    print(data)

    data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["is_paid"] = False



    # 🔥 파일에서 다시 불러오고 추가하기
    if os.path.exists(ORDER_FILE):
        with open(ORDER_FILE, "r", encoding="utf-8") as f:
            saved_orders = json.load(f)
    else:
        saved_orders = []

    saved_orders.append(data)

    with open(ORDER_FILE, "w", encoding="utf-8") as f:
        json.dump(saved_orders, f, ensure_ascii=False, indent=2)

    return {"message": "주문 저장 완료"}

# 주문 리스트 가져오기
@app.get("/get-orders")
async def get_orders():
    if os.path.exists(ORDER_FILE):
        with open(ORDER_FILE, "r", encoding="utf-8") as f:
            saved_orders = json.load(f)
        return saved_orders
    else:
        return []

# 주문 결제 완료 처리
@app.post("/mark-paid/{order_index}")
async def mark_paid(order_index: int):
    if os.path.exists(ORDER_FILE):
        with open(ORDER_FILE, "r", encoding="utf-8") as f:
            saved_orders = json.load(f)

        if 0 <= order_index < len(saved_orders):
            saved_orders[order_index]["is_paid"] = True

            with open(ORDER_FILE, "w", encoding="utf-8") as f:
                json.dump(saved_orders, f, ensure_ascii=False, indent=2)

            return {"message": "결제 완료 처리"}
    return {"error": "잘못된 주문 번호"}

# 주문 삭제
@app.post("/delete-order/{order_index}")
async def delete_order(order_index: int):
    if os.path.exists(ORDER_FILE):
        with open(ORDER_FILE, "r", encoding="utf-8") as f:
            saved_orders = json.load(f)

        if 0 <= order_index < len(saved_orders):
            saved_orders.pop(order_index)  # 메모리에서도 삭제

            with open(ORDER_FILE, "w", encoding="utf-8") as f:
                json.dump(saved_orders, f, ensure_ascii=False, indent=2)

            return {"message": "주문 삭제 성공"}
    return {"error": "삭제 실패"}

# 정적 파일 제공 (이미지, css)
app.mount("/static", StaticFiles(directory="static"), name="static")
