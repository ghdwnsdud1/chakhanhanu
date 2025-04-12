# menus.py

# 🐷 돼지고기 메뉴
pork_menus = [
    {"id": "item_samgyeop", "label": "삼겹살", "price": 2967},
    {"id": "item_ogyeop", "label": "오겹살", "price": 3134},
    {"id": "item_moksal", "label": "목살", "price": 2634},
    # 추가 메뉴 예시
    {"id": "item_galbisal", "label": "갈비살", "price": 3400},
    {"id": "item_pig_jowl", "label": "항정살", "price": 3220},
]

# 🐮 소고기 (한우 1++) 메뉴
beef_menus = [
    {"id": "item_hanwoo_kkot", "label": "한우 꽃등심", "price": 18800},
    {"id": "item_hanwoo_chaekkkeut", "label": "한우 채끝등심", "price": 18000},
    {"id": "item_hanwoo_ansim", "label": "한우 안심", "price": 18800},
    # 추가 메뉴 예시
    {"id": "item_hanwoo_satae", "label": "한우 사태", "price": 12900},
    {"id": "item_hanwoo_chadol", "label": "한우 차돌박이", "price": 15600},
]

# id -> label 이름 맵 (주문 확인용)
ITEM_NAME_MAP = {item["id"]: item["label"] for item in pork_menus + beef_menus}
