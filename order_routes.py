# order_routes.py
from fastapi import APIRouter, Request
from bson import ObjectId
from pydantic import BaseModel
from datetime import datetime
import pytz
import os
from fastapi.responses import JSONResponse, HTMLResponse
import secrets
from pymongo import MongoClient
from dotenv import load_dotenv
from payment_routes import get_portone_token, verify_payment
from typing import List, Dict, Optional
from fastapi.templating import Jinja2Templates
import requests

templates = Jinja2Templates(directory="templates")


# MongoDB 연결
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["meatshop"]
orders_collection = db["orders"]

router = APIRouter()

# ✅ 주문 모델
class Order(BaseModel):
    items: List[Dict]  # ✅ 구조 명확히 지정
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
    timestamp: Optional[str] = ''
    imp_uid: Optional[str] = ''  # ✅ snake_case

# ✅ 주문 저장
@router.post("/submit-order")
async def submit_order(order: Order):
    print("🔥 주문 들어옴")
    korea = pytz.timezone('Asia/Seoul')
    now_korea = datetime.now(korea).strftime("%Y-%m-%d %H:%M:%S")

    order_dict = order.dict()

    # ✅ token 생성
    order_token = secrets.token_urlsafe(8)  # 예: h3X1QbD2
    order_dict["token"] = order_token

    # 기본값: 무조건 미결제
    order_dict["isPaid"] = False

    imp_uid = order_dict.get("imp_uid", "")

    if order_dict.get("paymentMethod") == "card" and imp_uid:
        token_res = get_portone_token()
        if not token_res:
            return JSONResponse(status_code=500, content={"message": "포트원 인증 실패"})

        access_token = token_res["response"]["access_token"]

        # 카드결제일 경우, 결제정보 확인
        payment_info = verify_payment(imp_uid, access_token)
        if payment_info.get("status") == "paid":
            order_dict["isPaid"] = True

    order_dict["timestamp"] = now_korea

    print("🔥 최종 저장될 order_dict:", order_dict)

    orders_collection.insert_one(order_dict)

    # ✅ 응답에 token 기반 주문조회 링크 포함
    return {
        "success": True,
        "message": "주문이 저장되었습니다.",
        "lookup_url": f"/order-lookup?token={order_token}"
    }

# ✅ 주문 목록 가져오기
@router.get("/get-orders")
async def get_orders():
    orders = list(orders_collection.find())
    for order in orders:
        order["_id"] = str(order["_id"])
    return orders

# ✅ 결제 완료 처리
@router.post("/mark-paid/{order_id}")
async def mark_paid(order_id: str):
    result = orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"isPaid": True}}
    )
    return {"message": "결제 완료 처리됨" if result.modified_count else "실패"}

# ✅ 주문 삭제
@router.post("/delete-order/{order_id}")
async def delete_order(order_id: str):
    result = orders_collection.delete_one({"_id": ObjectId(order_id)})
    return {"success": bool(result.deleted_count)}


@router.get("/order-lookup", response_class=HTMLResponse)
async def order_lookup(request: Request, token: str):
    order = orders_collection.find_one({"token": token})
    if not order:
        return templates.TemplateResponse("order_lookup.html", {"request": request, "error": "주문을 찾을 수 없습니다."})
    
    return templates.TemplateResponse("order_lookup.html", {
        "request": request,
        "order": order
    })
# ✅ 고객 주문 취소 요청 API (비동기 MongoDB이므로 await 필요!)
@router.post("/request-cancel-by-token")
async def request_cancel_by_token(request: Request):
    body = await request.json()
    token = body.get("token")
    if not token:
        return JSONResponse(status_code=400, content={"message": "토큰이 없습니다."})

    result = orders_collection.update_one( 
        {"token": token},
        {"$set": {"cancelRequested": True}}
    )

    if result.matched_count == 0:
        return JSONResponse(status_code=404, content={"message": "주문을 찾을 수 없습니다."})

    return {"message": "📩 취소 요청이 접수되었습니다. 운영팀이 확인 후 처리합니다."}


# ✅ PortOne 액세스 토큰 요청 함수 (동기 → await 쓰면 안 됨)
def get_portone_token():
    try:
        url = "https://api.iamport.kr/users/getToken"
        headers = {"Content-Type": "application/json"}
        data = {
            "imp_key": os.getenv("PORTONE_API_KEY"),
            "imp_secret": os.getenv("PORTONE_API_SECRET")
        }

        res = requests.post(url, json=data, headers=headers)
        result = res.json()

        print("🔐 PortOne 응답:", result)

        if res.status_code == 200 and result.get("code") == 0:
            return result  # 전체 JSON 반환
        else:
            print("❌ PortOne 토큰 요청 실패:", result)
            return None

    except Exception as e:
        print("❌ PortOne 토큰 요청 중 예외 발생:", e)
        return None


# ✅ 관리자 결제 취소 승인 처리
@router.post("/cancel-order")
async def cancel_order(request: Request):
    print("🧠 DEBUG: cancel-order 코드 반영됨!")
    try:
        body = await request.json()
        order_id = body.get("order_id")

        order = await orders_collection.find_one({"_id": ObjectId(order_id)})
        if not order or not order.get("isPaid") or not order.get("imp_uid"):
            return JSONResponse(status_code=400, content={"success": False, "message": "결제된 주문만 취소할 수 있습니다."})

        token_res = get_portone_token()  # ✅ await ❌ (동기 함수)
        if not token_res:
            return JSONResponse(status_code=500, content={"success": False, "message": "PortOne 인증 실패"})

        access_token = token_res["response"]["access_token"]

        # ✅ await ❌ (requests는 동기)
        cancel_res = requests.post(
            "https://api.iamport.kr/payments/cancel",
            headers={"Authorization": access_token},
            json={"imp_uid": order["imp_uid"], "reason": "고객 요청 취소"}
        ).json()

        if cancel_res.get("code") == 0:
            await orders_collection.update_one(
                {"_id": ObjectId(order_id)},
                {"$set": {"isPaid": False, "isCanceled": True, "cancelRequested": False}}
            )
            return JSONResponse(content={"success": True, "message": "✅ 결제가 취소되었습니다."})
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "PG사 취소 실패: " + cancel_res.get("message", "")}
            )

   except Exception as e:
    import traceback
    print("🔥 서버 에러:", str(e))
    traceback.print_exc()  # ✅ 이 줄 추가!
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "서버 에러 발생", "detail": str(e)}
    )