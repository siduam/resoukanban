import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

FONT_PATH = "font.ttf"
try:
    font_title = ImageFont.truetype(FONT_PATH, 24)
    font_item = ImageFont.truetype(FONT_PATH, 18)
    font_small = ImageFont.truetype(FONT_PATH, 14)
except:
    print("错误: 找不到 font.ttf")
    exit(1)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ================= 核心工具函数：智能换行与动态绘图 =================

def get_wrapped_lines(text, max_chars=18):
    """根据字数手动换行，确保中英文混合不乱码"""
    lines = []
    while text:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    return lines

def draw_dynamic_hot_list(draw, title, all_items, start_idx=0):
    """
    动态布局函数：自动计算高度，填满即止
    返回：本页显示的最后一个条目的索引
    """
    # 绘制你喜欢的黑底标题栏
    draw.rounded_rectangle([(10, 10), (390, 45)], radius=8, fill=0)
    draw.text((20, 15), title, font=font_title, fill=255)
    
    y = 55
    item_gap = 12
    line_height = 22
    last_idx = start_idx
    
    for i in range(start_idx, len(all_items)):
        text = all_items[i]
        lines = get_wrapped_lines(text, max_chars=19)
        
        # 计算这一条总共需要的高度
        required_h = len(lines) * line_height
        
        # 如果当前高度 + 所需高度 超过屏幕底部（留点边距），则停止
        if y + required_h > 290:
            break
            
        # 绘制序号（根据你的要求，保留前5个有黑框的icon效果，之后的只显示数字）
        current_num = i + 1
        if current_num <= 5:
            draw.rounded_rectangle([(10, y), (34, y+24)], radius=6, fill=0)
            draw.text((16 if current_num < 10 else 12, y+2), str(current_num), font=font_small, fill=255)
        else:
            draw.text((15, y+2), f"{current_num}.", font=font_item, fill=0)
            
        # 绘制多行标题
        curr_y = y + 2
        for line in lines:
            draw.text((45, curr_y), line, font=font_item, fill=0)
            curr_y += line_height
            
        # 动态更新 y 坐标
        y += max(24, required_h) + item_gap
        last_idx = i + 1 # 记录处理到了第几条
        
        # 绘制淡淡的分割线
        if y < 285:
            draw.line([(45, y - item_gap/2), (380, y - item_gap/2)], fill=0, width=1)
            
    return last_idx

def push_image(img, page_id):
    img.save("temp.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": ("temp.png", open("temp.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    try:
        res = requests.post(PUSH_URL, headers=api_headers, files=files, data=data)
        print(f"推送第 {page_id} 页成功:", res.status_code)
    except Exception as e:
        print(f"推送第 {page_id} 页失败:", e)

# ================= 页面执行任务 =================

def page_zhihu():
    print("获取知乎热榜...")
    try:
        u
