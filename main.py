import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
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

# ================= 核心工具函数 =================

def get_wrapped_lines(text, max_chars=18):
    """手动换行函数"""
    lines = []
    while text:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    return lines

def draw_dynamic_hot_list(draw, title, all_items, start_idx=0):
    """
    通用动态排版函数：统一黑底方块编号风格
    """
    # 顶部黑底标题栏
    draw.rounded_rectangle([(10, 10), (390, 45)], radius=8, fill=0)
    draw.text((20, 15), title, font=font_title, fill=255)
    
    y = 55
    item_gap = 12
    line_height = 22
    last_idx = start_idx
    
    for i in range(start_idx, len(all_items)):
        text = all_items[i]
        lines = get_wrapped_lines(text, max_chars=19)
        required_h = len(lines) * line_height
        
        # 屏幕保护：如果放不下了就停止
        if y + required_h > 295:
            break
            
        # --- 统一编号风格：全员黑底方块 ---
        current_num = i + 1
        draw.rounded_rectangle([(10, y), (36, y+24)], radius=6, fill=0)
        # 数字居中：1位数和2位数位移不同
        num_x = 18 if current_num < 10 else 11
        draw.text((num_x, y+2), str(current_num), font=font_small, fill=255)
            
        # 绘制文本
        curr_y = y + 2
        for line in lines:
            draw.text((45, curr_y), line, font=font_item, fill=0)
            curr_y += line_height
            
        y += max(24, required_h) + item_gap
        last_idx = i + 1 
        
        # 绘制分割线
        if y < 290:
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
    except:
        print(f"推送第 {page_id} 页失败")

# ================= 任务流程 =================

# 1. 知乎热榜 (Page 1 & 2)
def task_zhihu():
    print("获取知乎热榜...")
    try:
        url = "https://api.zhihu.com/topstory/hot-list"
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        titles = [item['target']['title'] for item in res['data']]
    except:
        titles = ["知乎数据获取失败"] * 10

    img1 = Image.new('1', (400, 300), color=255)
    next_start = draw_dynamic_hot_list(ImageDraw.Draw(img1), "🔥 知乎热榜 (一)", titles, 0)
    push_image(img1, 1)

    img2 = Image.new('1', (400, 300), color=255)
    draw_dynamic_hot_list(ImageDraw.Draw(img2), "🔥 知乎热榜 (二)", titles, next_start)
    push_image(img2, 2)

# 2. AI & 机器人新闻 (Page 3)
def task_ai_news():
    print("获取 AI 与科技资讯...")
    news_titles = []
    try:
        # 使用 IT之家 科技热榜作为来源，AI/机器人资讯非常多
        url = "https://api.vvhan.com/api/hotlist/itNews"
        res = requests.get(url, timeout=10).json()
        if res.get('success'):
            for item in res['data'][:10]:
                news_titles.append(item['title'])
    except:
        news_titles = ["AI 新闻获取失败，请稍后重试"]
        
    img = Image.new('1', (400, 300), color=255)
    # 同样使用动态排版和统一的黑底编号
    draw_dynamic_hot_list(ImageDraw.Draw(img), "🤖 AI 与机器人资讯", news_titles)
    push_image(img, 3)

# 3. 综合看板 (Page 4)
def task_dashboard():
    print("生成综合看板...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    try:
        url = "http://t.weather.itboy.net/api/weather/city/101030100" # 天津
        weather = requests.get(url, timeout=10).json()
        city = weather['cityInfo']['city']
        data = weather['data']['forecast'][0]
        wea_str = f"{city} | {data['type']}"
        temp_str = f"{data['low'].replace('低温 ','')}~{data['high'].replace('高温 ','')}"
        tip = data['notice']
    except:
        wea_str, temp_str, tip = "天津 | 未知", "0~0℃", "获取失败"

    # 天气与倒计时方块样式
    draw.rounded_rectangle([(10, 10), (195, 120)], radius=10, fill=0)
    draw.text((20, 20), wea_str, font=font_title, fill=255)
    draw.text((20, 60), temp_str, font=font_title, fill=255)
    
    days_to_weekend = 5 - datetime.today().weekday()
    draw.rounded_rectangle([(205, 10), (390, 120)], radius=10, fill=0)
    draw.text((215, 20), "距离周末", font=font_item, fill=255)
    draw.text((215, 60), "已是周末!" if days_to_weekend <= 0 else f"还有 {days_to_weekend} 天", font=font_title, fill=255)

    # 建议
    draw.text((10, 135), "👕 建议:", font=font_item, fill=0)
    tip_lines = get_wrapped_lines(tip, 19)
    for i, line in enumerate(tip_lines[:2]):
        draw.text((10, 160 + i*22), line, font=font_item, fill=0)

    # 每日一言
    try:
        hito = requests.get("https://v1.hitokoto.cn/?c=i", timeout=5).json()['hitokoto']
    except:
        hito = "保持热爱，奔赴山海。"
        
    draw.line([(10, 220), (390, 220)], fill=0, width=2)
    draw.text((10, 230), "「每日一言」", font=font_small, fill=0)
    hito_lines = get_wrapped_lines(hito, 20)
    for i, line in enumerate(hito_lines[:2]):
        draw.text((10, 250 + i*25), line, font=font_item, fill=0)

    push_image(img, 4)

if __name__ == "__main__":
    task_zhihu()     # 页面 1 & 2
    task_ai_news()   # 页面 3 (新替换内容)
    task_dashboard() # 页面 4
    print("全部执行完毕！")
