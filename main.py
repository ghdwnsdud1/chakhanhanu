from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

# 1. FastAPI 앱 생성
app = FastAPI()

# 2. 미들웨어 등록
app.add_middleware(SessionMiddleware, secret_key="supersecretkey123")

# 3. 라우터 import 및 등록 (미들웨어 이후!)
from payment_routes import router as payment_router
from admin_routes import router as admin_router
from order_routes import router as order_router
from misc_routes import router as misc_router

app.include_router(payment_router)
app.include_router(admin_router)
app.include_router(order_router)
app.include_router(misc_router)
