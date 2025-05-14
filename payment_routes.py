# payment_routes.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import requests
from db import orders_collection

router = APIRouter()

@router.post("/payment-result")
async def payment_result(request: Request):
    form_data = await request.form()
    print("💳 [payment-result] 결제 결과 수신:", dict(form_data))
    
    order_oid = form_data.get("P_OID", "").replace("order_", "")

    try:
        if order_oid:
            orders_collection.update_one(
                {"_id": ObjectId(order_oid)},
                {"$set": {"is_paid": True}}
            )
    except Exception as e:
        print("결제 상태 업데이트 실패:", e)

# 여기에 결제 검증/주문 업데이트 가능
    return RedirectResponse(url="/success")

@router.post("/payment-notify")
async def payment_notify(request: Request):
    form_data = await request.form()
    print("🔔 [payment-notify] 결제 서버 알림 수신:", dict(form_data))
    # 서버에서 비동기 결제 정보 수신 → 검증 후 주문 업데이트
    return "OK"

def get_portone_token():
    url = "https://api.iamport.kr/users/getToken"
    data = {
        "imp_key": "8707636126083037",
        "imp_secret": "b28c8bSZwttod8gCyCspOtQIwUxsuBe7dYWbzHW3dWsjIcwqfVoaLPdgQbn75FvXYrLR49ySZlYklprg"
    }
    response = requests.post(url, data=data).json()
    return response['response']['access_token']

def verify_payment(imp_uid, access_token):
    url = f"https://api.iamport.kr/payments/{imp_uid}"
    headers = {
        "Authorization": access_token
    }
    response = requests.get(url, headers=headers).json()
    return response['response']

@router.get("/mobile-payment-success", response_class=HTMLResponse)
async def mobile_payment_success(request: Request):
    return templates.TemplateResponse("mobile_success.html", {"request": request})
