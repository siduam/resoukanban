import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# ================= 配置区 =================
# 从 GitHub Secrets 保险箱里读取密码，开源绝对安全！
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

# 字体设置 (请确保你的仓库里上传了 font.ttf)
FONT_PATH = "font.ttf"
try:
    font_title = ImageFont.truetype(FONT_PATH, 24)
    font_item = ImageFont.truetype(FONT_PATH, 18)
    font_small = ImageFont.truetype(FONT_PATH, 14)
    font_large = ImageFont.truetype(FONT_PATH, 40)
except:
    print("错误: 找不到 font.ttf 字体文件，请确保它已上传到仓库！")
    exit(1)

# ================= 绘图辅助函数 =================
def draw_newsnow_style_list(draw, title, items):
    """绘制类似 NewsNow 风格的列表"""
    # 标题背景
    draw.rounded_rectangle([(10, 10), (390, 45)], radius=8, fill=0)
    draw.text((20, 15), title, font=font_title, fill=255)
    
    y = 55
    for i, text in enumerate(items[:8]): # 显示前8条
        # 绘制序号的黑底白字圆角框
        box_w, box_h = 24, 24
        draw.rounded_rectangle([(10, y), (10+box_w, y+box_h)], radius=6, fill=0)
        # 序号数字居中
        draw.text((16 if i<9 else 12, y+2), str(i+1), font=font_small, fill=255)
        
        # 截断过长的文字
        if len(text) > 20:
            text = text[:19] + "..."
        # 绘制新闻标题
        draw.text((45, y+2), text, font=font_item, fill=0)
        y += 30

# ================= 数据获取与页面生成 =================

def push_image(img, page_id):
    """推送到墨水屏"""
    img.save("temp.png")
    headers = {"X-API-Key": API_KEY}
    files = {"images": ("temp.png", open("temp.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    res = requests.post(PUSH_URL, headers=headers, files=files, data=data)
    print(f"推送第 {page_id} 页结果:", res.status_code)

def page1_weibo():
    print("正在生成微博热搜...")
    img = Image.new('RGB', (400, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        res = requests.get("https://api.vvhan.com/api/hotlist/wbHot").json()
        items = [item['title'] for item in res['data']]
    except:
        items =["获取数据失败..."] * 8
        
    draw_newsnow_style_list(draw, "🔥 微博实时热搜", items)
    push_image(img, page_id=1)

def page2_github():
    print("正在生成 GitHub 趋势...")
    img = Image.new('RGB', (400, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        res = requests.get("https://api.vvhan.com/api/hotlist/github").json()
        items = [item['title'] for item in res['data']]
    except:
        items = ["获取数据失败..."] * 8
        
    draw_newsnow_style_list(draw, "💻 GitHub 趋势榜", items)
    push_image(img, page_id=2)

def page3_dashboard():
    print("正在生成综合看板...")
    img = Image.new('RGB', (400, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # 1. 绘制顶部：天气信息 (左边)
    try:
        weather_data = requests.get("https://api.vvhan.com/api/weather").json()
        city = weather_data['city']
        wea = weather_data['info']['type']
        high = weather_data['info']['high']
        low = weather_data['info']['low']
        tip = weather_data['info']['tip']
    except:
        city, wea, high, low, tip = "未知", "未知", "0℃", "0℃", "天气获取失败"

    draw.rounded_rectangle([(10, 10), (195, 120)], radius=10, fill=0)
    draw.text((20, 20), f"{city} | {wea}", font=font_title, fill=255)
    draw.text((20, 55), f"{low} ~ {high}", font=font_item, fill=255)
    
    # 2. 绘制右侧：周末倒计时
    today = datetime.today().weekday() # 0是周一，4是周五
    days_to_weekend = 5 - today
    if days_to_weekend <= 0:
        countdown_text = "已是周末!"
    else:
        countdown_text = f"还有 {days_to_weekend} 天"
        
    draw.rounded_rectangle([(205, 10), (390, 120)], radius=10, fill=0)
    draw.text((215, 20), "距离周末", font=font_item, fill=255)
    draw.text((215, 50), countdown_text, font=font_large, fill=255)

    # 3. 绘制中间：穿衣/生活建议
    draw.text((10, 135), "📌 建议:", font=font_item, fill=0)
    # 简单换行处理
    tip_line1 = tip[:18]
    tip_line2 = tip[18:36] + "..." if len(tip) > 36 else tip[18:]
    draw.text((10, 160), tip_line1, font=font_item, fill=0)
    draw.text((10, 185), tip_line2, font=font_item, fill=0)

    # 4. 绘制底部：每日一言
    try:
        hitokoto = requests.get("https://v1.hitokoto.cn/?c=a").json()['hitokoto']
    except:
        hitokoto = "永远年轻，永远热泪盈眶。"
        
    draw.line([(10, 220), (390, 220)], fill=0, width=2)
    draw.text((10, 230), "「每日一言」", font=font_small, fill=0)
    
    hito_line1 = hitokoto[:20]
    hito_line2 = hitokoto[20:40] + "..." if len(hitokoto) > 40 else hitokoto[20:]
    draw.text((10, 250), hito_line1, font=font_item, fill=0)
    draw.text((10, 275), hito_line2, font=font_item, fill=0)

    push_image(img, page_id=3)

# ================= 主程序执行 =================
if __name__ == "__main__":
    if not API_KEY or not MAC_ADDRESS:
        print("错误: 找不到 API_KEY 或 MAC_ADDRESS 环境变量！")
        exit(1)
        
    page1_weibo()
    page2_github()
    page3_dashboard()
    print("全部执行完毕！")
