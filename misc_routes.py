# misc_routes.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import csv, io

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def order_form(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})

@router.get("/success", response_class=HTMLResponse)
async def success(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

@router.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})

@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

@router.get("/get-products")
def get_products_from_sheet():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQI58uFg2f8bnhecmETQCYUHM9TjNfI4RzLpYB5pDtcoxb5l4tIyB85-BeCv10auhzMlZL5rXIj8_uY/pub?output=csv"
    
    response = requests.get(url)
    response.encoding = 'utf-8'
    content = response.content.decode("utf-8")

    reader = csv.DictReader(io.StringIO(content))
    products = []

    for row in reader:
        try:
            product = {
                "name": row["name"].strip(),
                "category": row["category"].strip(),
                "price": int(row["price"].strip()),
                "status": row["status"].strip().replace('\r', '')
            }
            products.append(product)
        except Exception as e:
            print(f"❌ 오류 발생: {e} → row={row}")

    return products