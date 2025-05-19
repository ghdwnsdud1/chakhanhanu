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
from typing import List, Optional
from collections import defaultdict, Counter
from pydantic import BaseModel
from collections import defaultdict, Counter
from datetime import datetime
from urllib.parse import quote

# ✅ 주문 데이터 모델
class Item(BaseModel):
    meat: str
    weight: int
    pricePerUnit: int
    type: str
    quantity: int

class Order(BaseModel):
    items: List[Item]
    totalAmount: str
    contact: str
    name: str
    address: str
    doorcode: Optional[str] = ''
    requestMessage: Optional[str] = ''
    deliveryRequest: Optional[str] = ''
    paymentMethod: str
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

# ✅ 관리자 로그인 정보
ADMIN_ID = "ghdwnsdud1"
ADMIN_PW = "0214"

# 로그인 페이지
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...), request: Request = None):
    if username == ADMIN_ID and password == ADMIN_PW:
        request.session["logged_in"] = True
        return RedirectResponse(url="/admin", status_code=302)
    return HTMLResponse(content="❌ 로그인 실패", status_code=401)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

# 관리자 대시보드 페이지
@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    # iframe에서만 허용하고, 외부 접근이면 redirect
    if request.headers.get("referer", "").endswith("/dashboard"):
        return templates.TemplateResponse("admin.html", {"request": request})
    return RedirectResponse(url="/dashboard")

# 배송일자 분류 (오후 2시 기준)
def determine_delivery_date(timestamp_str):
    try:
        korea = pytz.timezone('Asia/Seoul')
        order_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        order_time = korea.localize(order_time)
        cutoff = order_time.replace(hour=14, minute=0, second=0, microsecond=0)
        return str(order_time.date() if order_time <= cutoff else (order_time + timedelta(days=1)).date())
    except Exception as e:
        print(f"배송일자 계산 실패: {e}")
        return "분류불가"

# 주문 목록
@router.get("/get-orders")
async def get_orders():
    orders = []
    for order in orders_collection.find({}).sort("timestamp", -1):
        order["_id"] = str(order["_id"])
        order["isPaid"] = order.get("isPaid", False)
        ts = order.get("timestamp")
        order["배송일자"] = determine_delivery_date(ts) if ts else "분류불가"
        orders.append(order)
    return JSONResponse(content=orders)

# 결제 완료 처리
@router.post("/mark-paid/{order_id}")
async def mark_paid(order_id: str):
    try:
        result = orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"isPaid": True}}
        )
        if result.modified_count == 1:
            return {"success": True}
        raise HTTPException(status_code=404, detail="Order not found")
    except Exception as e:
        print(f"❌ 결제완료 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail="Server error")

# 엑셀 다운로드
@router.get("/download-orders")
async def download_orders():
    orders = list(orders_collection.find())
    korea = pytz.timezone('Asia/Seoul')
    today = datetime.now(korea).date()
        
# ✅ 오늘 배송할 주문만 필터링
    filtered_orders = []
    for order in orders:
        ts = order.get("timestamp", "")
        delivery_date = determine_delivery_date(ts)
        
        if isinstance(delivery_date, str):
            try:
                delivery_date = datetime.strptime(delivery_date, "%Y-%m-%d").date()
            except:
                continue
  
        if delivery_date == today:
            order["_id"] = str(order["_id"])
            order["배송일자"] = delivery_date
            filtered_orders.append(order)

# ✅ grouped 기준도 필터된 주문 기준
    grouped = defaultdict(list)
    for order in filtered_orders:
        key = f"{order.get('name', '-')}_{order.get('contact', '-')}_{order['배송일자']}"
        grouped[key].append(order)

    rows = []
    for key, group in grouped.items():
        name, contact, delivery = key.split("_")
        item_summary = defaultdict(int)
        requests = []
        isPaid = False

        for o in group:
            items = o.get("items", [])
            for item in items:
                meat = item.get("meat", "-")
                weight = item.get("weight", 0)
                quantity = item.get("quantity", 1)
                item_type = item.get("type", "")
                unit = "개" if item_type == "marinated" else "g"

                key_name = f"{meat} ({unit})"
                if unit == "개":
                    item_summary[key_name] += quantity
                else:
                    item_summary[key_name] += weight
  
            msg = o.get("requestMessage", "")
            if msg:
                requests.append(msg)

            if o.get("isPaid", False):
                isPaid = True
        all_items = [
    f"{meat.replace(' (g)', '').replace(' (개)', '')} {amount}{'g' if '(g)' in meat else '개'}"
    for meat, amount in item_summary.items()
]
        rows.append({
            "이름": name,
            "연락처": contact,
            "주소": group[0].get("address", ""),
            "배송일자": delivery,
            "주문상품": ", ".join(all_items),
            "결제상태": "완료" if isPaid else "미완료",
            "요청사항": " / ".join(requests) if requests else "-"
        })

    df = pd.DataFrame(rows)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='주문내역')
        worksheet = writer.sheets['주문내역']
        bold_font = Font(name='맑은 고딕', size=13)
        align = Alignment(wrap_text=True, vertical='top')
        for row in worksheet.iter_rows():
            for cell in row:
                cell.font = bold_font
                cell.alignment = align
        for col, width in zip(['A', 'B', 'C', 'D', 'E', 'F'], [14, 20, 14, 50, 12, 50]):
            worksheet.column_dimensions[col].width = width

    output.seek(0)
    filename = quote("주문내역.xlsx")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
)


# 📊 통계 API
@router.get("/admin/stats")
async def get_stats():
    orders = list(orders_collection.find({}))
    time_slots = defaultdict(int)
    weekdays = defaultdict(int)

    menu_counter = Counter()
    unit_map = {}
    display_unit_map = {}
    order_time_stats = {"00시~10시": 0,"10시~14시": 0, "14시~18시": 0, "18시 이후": 0}
    payment_stats = defaultdict(int)
    contact_counter = Counter()
    monthly_orders = defaultdict(int)

    for order in orders:
        # 주문 항목별 인기메뉴 집계
        for item in order.get("items", []):
            name = item.get("meat")
            item_type = item.get("type", "")
            weight = item.get("weight", 0)
            quantity = item.get("quantity", 1)
            if not name:
                continue

            # ✅ 간편식: 1개 = 100g × 수량
            if item_type in ["marinated", "processed", "easy", "meal", "ready"]:
                menu_counter[name] += 100 * quantity
                unit_map[name] = "g"
                if name not in display_unit_map:
                    display_unit_map[name] = 0
                display_unit_map[name] += quantity
            else:
                menu_counter[name] += weight
                unit_map[name] = "g"
                display_unit_map[name] = "g"

        # ✅ 시간대/요일 통계
        timestamp_str = order.get("timestamp")
        if not timestamp_str:
            continue
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except:
            continue

        hour = dt.hour
        if 0 <= hour < 10:
            order_time_stats["00시~10시"] += 1
        if 10 <= hour < 14:
            order_time_stats["10시~14시"] += 1
        elif 14 <= hour < 18:
            order_time_stats["14시~18시"] += 1
        elif hour >= 18:
            order_time_stats["18시 이후"] += 1

        weekday_name = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
        weekdays[weekday_name] += 1

        # ✅ 결제 수단 금액 합계
        method = order.get("paymentMethod", "unknown")
        try:
            amount = int(order["totalAmount"].replace(",", "").replace("원", ""))
            payment_stats[method] += amount
        except:
            pass

        # ✅ 재주문율 집계
        contact = order.get("contact", "")
        if contact:
            contact_counter[contact] += 1

        # ✅ 월별 주문 수
        month_key = dt.strftime("%Y-%m")
        monthly_orders[month_key] += 1

    # ✅ 주문 통계 최종 계산
    repeat_users = sum(1 for c in contact_counter.values() if c > 1)
    repeat_rate = repeat_users / len(contact_counter) if contact_counter else 0
    average_order_per_user = len(orders) / len(contact_counter) if contact_counter else 0

    top_menus = {
        name: {
            "value": total,
            "unit": unit_map.get(name, "g"),
            "displayUnit": f"{display_unit_map[name]}개" if isinstance(display_unit_map[name], int) else "g"
        }
        for name, total in menu_counter.most_common()
    }

    return {
        "topMenus": top_menus,
        "orderTimeStats": order_time_stats,
        "paymentStats": dict(payment_stats),
        "repeatRate": round(repeat_rate, 4),
        "monthlyOrders": dict(monthly_orders),
        "averageOrderPerUser": round(average_order_per_user, 2),
        "time_slots": dict(sorted(time_slots.items())),
        "weekdays": dict(weekdays)
    }

