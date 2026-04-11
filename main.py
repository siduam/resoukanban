import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

# 字体设置 (确保 GitHub 仓库里有 font.ttf，也就是你下载的霞鹜文楷)
FONT_PATH = "font.ttf"
try:
    font_title = ImageFont.truetype(FONT_PATH, 24)
    font_item = ImageFont.truetype(FONT_PATH, 18)
    font_small = ImageFont.truetype(FONT_PATH, 14)
    font_large = ImageFont.truetype(FONT_PATH, 40)
except:
    print("错误: 找不到 font.ttf")
    exit(1)

# 全局请求头，伪装成普通浏览器，防止被微博等网站拦截
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ================= 绘图辅助函数 =================
def draw_newsnow_style_list(draw, title, items):
    """绘制类似 NewsNow 风格的列表"""
    draw.rounded_rectangle([(10, 10), (390, 45)], radius=8, fill=0)
    draw.text((20, 15), title, font=font_title, fill=255)
    
    y = 55
    for i, text in enumerate(items[:8]): # 显示前8条
        box_w, box_h = 24, 24
        draw.rounded_rectangle([(10, y), (10+box_w, y+box_h)], radius=6, fill=0)
        draw.text((16 if i<9 else 12, y+2), str(i+1), font=font_small, fill=255)
        
        # 截断过长的文字，防止超出屏幕边缘
        if len(text) > 19:
            text = text[:18] + "..."
        draw.text((45, y+2), text, font=font_item, fill=0)
        y += 30

def push_image(img, page_id):
    """推送到墨水屏"""
    img.save("temp.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": ("temp.png", open("temp.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    
    try:
        res = requests.post(PUSH_URL, headers=api_headers, files=files, data=data)
        print(f"推送第 {page_id} 页成功:", res.status_code)
    except Exception as e:
        print(f"推送第 {page_id} 页失败:", e)

# ================= 页面 1：微博热搜 =================
def page1_weibo():
    print("获取微博热搜...")
    img = Image.new('1', (400, 300), color=255) # 使用 '1' 模式（纯黑白）让文字更锐利
    draw = ImageDraw.Draw(img)
    
    items = []
    try:
        # 直接调用微博官方隐藏 API
        url = "https://weibo.com/ajax/side/hotSearch"
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        for item in res['data']['realtime']:
            if 'word' in item:
                items.append(item['word'])
    except Exception as e:
        print("微博获取报错:", e)
        items = ["获取数据失败，请检查网络..."] * 8
        
    draw_newsnow_style_list(draw, "🔥 微博实时热搜", items)
    push_image(img, page_id=1)

# ================= 页面 2：GitHub 趋势 =================
def page2_github():
    print("获取 GitHub 趋势...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    items = []
    try:
        # 调用 GitHub 官方 API 获取最近 7 天最热项目
        last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = f"https://api.github.com/search/repositories?q=created:>{last_week}&sort=stars&order=desc"
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        for item in res['items'][:8]:
            repo_name = item['name']
            stars = item['stargazers_count']
            items.append(f"{repo_name} ({stars}★)")
    except Exception as e:
        print("GitHub获取报错:", e)
        items = ["获取数据失败，请检查网络..."] * 8
        
    draw_newsnow_style_list(draw, "💻 GitHub 热门开源", items)
    push_image(img, page_id=2)

# ================= 页面 3：综合看板 =================
def page3_dashboard():
    print("生成综合看板...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    # --- 1. 天气模块 ---
    try:
        # 稳定的免费天气接口，101030100 是天津。北京是 101010100。
        url = "http://t.weather.itboy.net/api/weather/city/101030100"
        weather_data = requests.get(url, headers=HEADERS, timeout=10).json()
        city = weather_data['cityInfo']['city']
        forecast = weather_data['data']['forecast'][0]
        wea = forecast['type']
        # 提取 "高温 28℃" 里的数字
        high = forecast['high'].replace('高温 ', '')
        low = forecast['low'].replace('低温 ', '')
        tip = forecast['notice']
    except Exception as e:
        print("天气获取报错:", e)
        city, wea, high, low, tip = "天津", "未知", "0℃", "0℃", "无法获取建议，请注意保暖。"

    # 画左上角天气黑框
    draw.rounded_rectangle([(10, 10), (195, 120)], radius=10, fill=0)
    draw.text((20, 20), f"{city} | {wea}", font=font_title, fill=255)
    draw.text((20, 60), f"{low} ~ {high}", font=font_title, fill=255)
    
    # --- 2. 倒计时模块 ---
    today = datetime.today().weekday() # 0是周一，4是周五
    days_to_weekend = 5 - today
    if days_to_weekend <= 0:
        countdown_text = "已是周末!"
    else:
        countdown_text = f"还有 {days_to_weekend} 天"
        
    # 画右上角倒计时黑框
    draw.rounded_rectangle([(205, 10), (390, 120)], radius=10, fill=0)
    draw.text((215, 20), "距离周末", font=font_item, fill=255)
    draw.text((215, 60), countdown_text, font=font_title, fill=255)

    # --- 3. 建议模块 ---
    draw.text((10, 135), "📌 建议:", font=font_item, fill=0)
    # 自动折行处理建议文字
    tip_line1 = tip[:18]
    tip_line2 = tip[18:36] + "..." if len(tip) > 36 else tip[18:]
    draw.text((10, 160), tip_line1, font=font_item, fill=0)
    draw.text((10, 185), tip_line2, font=font_item, fill=0)

    # --- 4. 每日一言模块 ---
    try:
        hitokoto = requests.get("https://v1.hitokoto.cn/?c=a", timeout=10).json()['hitokoto']
    except:
        hitokoto = "永远年轻，永远热泪盈眶。"
        
    draw.line([(10, 220), (390, 220)], fill=0, width=2)
    draw.text((10, 230), "「每日一言」", font=font_small, fill=0)
    
    # 自动折行处理一言
    hito_line1 = hitokoto[:20]
    hito_line2 = hitokoto[20:40] + "..." if len(hitokoto) > 40 else hitokoto[20:]
    draw.text((10, 250), hito_line1, font=font_item, fill=0)
    draw.text((10, 275), hito_line2, font=font_item, fill=0)

    push_image(img, page_id=3)

# ================= 主程序执行 =================
if __name__ == "__main__":
    if not API_KEY or not MAC_ADDRESS:
        print("错误: 请先在 GitHub Secrets 中配置 ZECTRIX_API_KEY 和 ZECTRIX_MAC")
        exit(1)
        
    page1_weibo()
    page2_github()
    page3_dashboard()
    print("全部执行完毕！")
