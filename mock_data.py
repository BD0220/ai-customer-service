"""
模拟数据模块
模拟电商平台的用户、订单、物流、商品数据。
实际生产中应替换为真实的数据库/API 调用。
"""

# ========== 用户数据 ==========
USERS = {
    "U10086": {
        "user_id": "U10086",
        "name": "张三",
        "phone": "138****8888",
        "level": "VIP",
    },
    "U10087": {
        "user_id": "U10087",
        "name": "李四",
        "phone": "139****9999",
        "level": "普通",
    },
}

# ========== 订单数据 ==========
ORDERS = {
    "ORD20260815001": {
        "order_id": "ORD20260815001",
        "user_id": "U10086",
        "status": "已发货",
        "status_code": "shipped",
        "created_at": "2026-08-15 10:23:45",
        "total_amount": 299.00,
        "items": [
            {"name": "纯棉圆领T恤", "sku": "TX-001-BLK-M", "qty": 2, "price": 89.00},
            {"name": "运动短裤", "sku": "DK-003-GRY-L", "qty": 1, "price": 121.00},
        ],
        "shipping_address": "浙江省杭州市西湖区文三路 100 号",
        "carrier": "顺丰速运",
        "tracking_no": "SF1234567890",
    },
    "ORD20260818002": {
        "order_id": "ORD20260818002",
        "user_id": "U10086",
        "status": "已签收",
        "status_code": "delivered",
        "created_at": "2026-08-18 14:05:12",
        "total_amount": 1599.00,
        "items": [
            {"name": "无线降噪耳机 Pro", "sku": "EP-500-BLK", "qty": 1, "price": 1599.00},
        ],
        "shipping_address": "浙江省杭州市西湖区文三路 100 号",
        "carrier": "京东物流",
        "tracking_no": "JD9876543210",
    },
    "ORD20260819003": {
        "order_id": "ORD20260819003",
        "user_id": "U10086",
        "status": "待发货",
        "status_code": "pending",
        "created_at": "2026-08-19 09:30:00",
        "total_amount": 458.00,
        "items": [
            {"name": "商务双肩包", "sku": "BG-200-BRN", "qty": 1, "price": 458.00},
        ],
        "shipping_address": "浙江省杭州市西湖区文三路 100 号",
        "carrier": None,
        "tracking_no": None,
    },
}

# ========== 物流数据 ==========
LOGISTICS = {
    "SF1234567890": {
        "tracking_no": "SF1234567890",
        "carrier": "顺丰速运",
        "status": "运输中",
        "estimated_delivery": "2026-08-20 18:00",
        "updates": [
            {"time": "2026-08-15 11:00", "location": "杭州", "action": "商家已发货"},
            {"time": "2026-08-15 18:30", "location": "杭州萧山转运中心", "action": "快件已发出"},
            {"time": "2026-08-16 08:15", "location": "杭州西湖区文三路营业点", "action": "快件到达，正在派送"},
            {"time": "2026-08-16 09:42", "location": "杭州西湖区", "action": "快递员已取件，配送中"},
        ],
    },
    "JD9876543210": {
        "tracking_no": "JD9876543210",
        "carrier": "京东物流",
        "status": "已签收",
        "estimated_delivery": "2026-08-19 15:00",
        "updates": [
            {"time": "2026-08-18 15:00", "location": "北京", "action": "商家已发货"},
            {"time": "2026-08-18 22:00", "location": "北京亦庄分拣中心", "action": "快件已发出"},
            {"time": "2026-08-19 10:00", "location": "杭州萧山分拣中心", "action": "快件到达"},
            {"time": "2026-08-19 14:30", "location": "杭州西湖区", "action": "已签收，签收人：本人"},
        ],
    },
}

# ========== 商品数据 ==========
PRODUCTS = [
    {
        "product_id": "P001",
        "name": "纯棉圆领T恤",
        "category": "服饰",
        "price": 89.00,
        "original_price": 129.00,
        "stock": 520,
        "specs": {"材质": "100%纯棉", "尺码": "S/M/L/XL/XXL", "颜色": "黑色/白色/雾霾蓝"},
        "description": "采用新疆长绒棉，柔软透气，经典圆领设计，百搭基础款。机洗不变形，不易褪色。",
        "tags": ["T恤", "纯棉", "夏季", "基础款"],
    },
    {
        "product_id": "P002",
        "name": "无线降噪耳机 Pro",
        "category": "数码",
        "price": 1599.00,
        "original_price": 1999.00,
        "stock": 86,
        "specs": {"蓝牙版本": "5.3", "续航": "40小时（含充电盒）", "降噪深度": "42dB", "重量": "5.2g/只"},
        "description": "主动降噪，Hi-Res 金标认证，40 小时超长续航，IPX5 防水。支持双设备连接。",
        "tags": ["耳机", "降噪", "蓝牙", "无线"],
    },
    {
        "product_id": "P003",
        "name": "商务双肩包",
        "category": "箱包",
        "price": 458.00,
        "original_price": 599.00,
        "stock": 200,
        "specs": {"材质": "防水牛津布", "容量": "25L", "适用": "15.6寸笔记本", "重量": "0.8kg"},
        "description": "商务通勤首选，防泼水面料，多隔层收纳，人体工学背带，减负透气。",
        "tags": ["双肩包", "商务", "通勤", "防水"],
    },
    {
        "product_id": "P004",
        "name": "运动短裤",
        "category": "服饰",
        "price": 121.00,
        "original_price": 169.00,
        "stock": 350,
        "specs": {"材质": "88%聚酯纤维+12%氨纶", "尺码": "M/L/XL/XXL", "颜色": "灰色/黑色/藏青"},
        "description": "速干面料，透气排汗，内置手机口袋，适合跑步、健身等运动场景。",
        "tags": ["短裤", "运动", "速干", "健身"],
    },
]


# ========== 查询函数 ==========

def get_user(user_id: str) -> dict | None:
    """根据 user_id 获取用户信息"""
    return USERS.get(user_id)


def get_order(order_id: str) -> dict | None:
    """根据订单号获取订单详情"""
    return ORDERS.get(order_id)


def get_user_orders(user_id: str) -> list[dict]:
    """获取某用户的所有订单"""
    return [o for o in ORDERS.values() if o["user_id"] == user_id]


def get_logistics(tracking_no: str) -> dict | None:
    """根据运单号获取物流信息"""
    return LOGISTICS.get(tracking_no)


def get_order_logistics(order_id: str) -> dict | None:
    """根据订单号获取物流信息（便捷方法）"""
    order = ORDERS.get(order_id)
    if order and order.get("tracking_no"):
        return LOGISTICS.get(order["tracking_no"])
    return None


def search_products(keyword: str) -> list[dict]:
    """根据关键词搜索商品（匹配名称、分类、标签）"""
    keyword = keyword.lower()
    results = []
    for p in PRODUCTS:
        if (keyword in p["name"].lower()
                or keyword in p["category"].lower()
                or any(keyword in tag.lower() for tag in p["tags"])):
            results.append(p)
    return results


def get_product(product_id: str) -> dict | None:
    """根据商品 ID 获取商品详情"""
    for p in PRODUCTS:
        if p["product_id"] == product_id:
            return p
    return None
