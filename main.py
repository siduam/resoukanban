import os
import requests
import calendar
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from zhdate import ZhDate

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

# 津南区天气代码 (天大北洋园)
CITY_CODE = "101030103" 

FONT_PATH = "font.ttf"
try:
    font_huge = ImageFont.truetype(FONT_PATH, 55)   # 月份大数字
    font_title = ImageFont.truetype(FONT_PATH, 24)  # 标题
    font_item = ImageFont.truetype(FONT_PATH, 18)   # 阳历/建议
    font_tiny = ImageFont.truetype(FONT_PATH, 11)   # 农历
    font_small = ImageFont.truetype(FONT_PATH, 14)  # 星期
except:
    print("错误: 找不到 font.ttf")
    exit(1)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ================= 辅助函数 =================

def get_clothing_advice(low, high):
    """根据气温给出具体的穿衣建议"""
    avg = (int(low) + int(high)) / 2
    if avg >= 28: return "天气炎热，建议穿短袖、短裤或短裙，注意防暑。"
    elif avg >= 22: return "体感凉爽，建议穿短袖 T 恤配长裤，或者一件长袖薄衫。"
    elif avg >= 16: return "气温适中，建议穿长袖衬衫、卫衣或单层薄外套。"
    elif avg >= 10: return "天气微凉，建议穿夹克、风衣或毛衣，注意保暖。"
    elif avg >= 5: return "气温较低，建议穿厚毛衣、大衣或薄羽绒服。"
    else: return "天气寒冷，建议穿厚羽绒服、保暖内衣，谨防感冒。"

def get_lunar_info(y, m, d):
    """获取精准农历，节日优先"""
    try:
        date_obj = datetime(y, m, d)
        lunar = ZhDate.from_datetime(date_obj)
        # 1. 法定节日
        fests = {(1,1):"元旦", (5,1):"劳动节", (10,1):"国庆节"}
        if (m, d) in fests: return fests[(m, d)]
        # 2. 农历节日
        l_fests = {(1,1):"春节", (5,5):"端午", (8,15):"中秋"}
        if (lunar.lunar_month, lunar.lunar_day) in l_fests:
            return l_fests[(lunar.lunar_month, lunar.lunar_day)]
        # 3. 节气 (清明单独逻辑)
        if m == 4 and (d == 4 or d == 5): return "清明"
        # 4. 普通农历日期 (如: 初八)
        return lunar.lunar_date_str()[-2:]
    except: return ""

def push_image(img, page_id):
    img.save(f"page_{page_id}.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": (f"page_{page_id}.png", open(f"page_{page_id}.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    requests.post(PUSH_URL, headers=api_headers, files=files, data=data)

# ================= Page 3: 实体台历风格 (完美对齐版) =================

def task_calendar():
    print("生成 Page 3: 实体台历...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    now = datetime.now()
    y, m, today = now.year, now.month, now.day
    
    # 顶部排版
    draw.text((20, 10), str(m), font=font_huge, fill=0)
    draw.text((85, 20), now.strftime("%B"), font=font_title, fill=0)
    draw.text((85, 48), str(y), font=font_item, fill=0)
    draw.line([(20, 78), (380, 78)], fill=0, width=2)

    # 星期头 (从周日开始)
    headers = ["日", "一", "二", "三", "四", "五", "六"]
    col_w = 53
    for i, h in enumerate(headers):
        draw.text((25 + i*col_w, 88), h, font=font_small, fill=0)

    # 绘制日历
    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(y, m)
    curr_y = 115
    row_h = 38
    
    for week in cal:
        for c, day in enumerate(week):
            if day != 0:
                dx = 25 + c*col_w
                # 绘制选中框（如果是今天）
                if day == today:
                    draw.rounded_rectangle([(dx-3, curr_y-2), (dx+36, curr_y+32)], radius=5, outline=0)
                
                # 阳历数字居中显示
                draw.text((dx+2, curr_y), str(day), font=font_item, fill=0)
                # 农历日期精准显示在数字正下方
                lunar_txt = get_lunar_info(y, m, day)
                draw.text((dx+2, curr_y + 18), lunar_txt, font=font_tiny, fill=0)
        curr_y += row_h
        
    push_image(img, 3)

# ================= Page 4: 综合看板 (精准天气+具体穿衣) =================

def task_dashboard():
    print("生成 Page 4: 综合看板 (津南)...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    try:
        # 重新回到国内稳定的 itboy 接口
        url = f"http://t.weather.itboy.net/api/weather/city/{CITY_CODE}"
        res = requests.get(url, timeout=10).json()
        city = res['cityInfo']['city']
        data = res['data']['forecast'][0]
        weather_type = data['type'] # 已经是中文，如 "多云"
        low_t = data['low'].replace('低温 ', '').replace('℃', '')
        high_t = data['high'].replace('高温 ', '').replace('℃', '')
        
        title_str = f"津南区 | {weather_type}"
        temp_range = f"{low_t}℃ ~ {high_t}℃"
        # 调用具体的穿衣逻辑
        clothing_advice = get_clothing_advice(low_t, high_t)
    except:
        title_str, temp_range, clothing_advice = "天大北洋园", "数据获取中", "获取天气失败，请关注室外气温。"

    # 天气与倒计时模块
    draw.rounded_rectangle([(10, 10), (195, 120)], radius=10, fill=0)
    draw.text((20, 20), title_str, font=font_title, fill=255)
    draw.text((20, 60), temp_range, font=font_title, fill=255)
    
    days = 5 - datetime.today().weekday()
    draw.rounded_rectangle([(205, 10), (390, 120)], radius=10, fill=0)
    draw.text((215, 20), "距离周末", font=font_item, fill=255)
    draw.text((215, 60), "已是周末!" if days <= 0 else f"还有 {days} 天", font=font_title, fill=255)

    # 具体穿衣建议
    draw.text((10, 135), "👕 建议:", font=font_item, fill=0)
    # 自动换行
    tip_lines = [clothing_advice[i:i+19] for i in range(0, len(clothing_advice), 19)]
    for i, line in enumerate(tip_lines[:2]):
        draw.text((10, 160 + i*22), line, font=font_item, fill=0)

    # 每日一言
    try: hito = requests.get("https://v1.hitokoto.cn/?c=i", timeout=5).json()['hitokoto']
    except: hito = "实事求是。"
        
    draw.line([(10, 220), (390, 220)], fill=0, width=2)
    draw.text((10, 230), "「每日一言」", font=font_small, fill=0)
    hito_lines = [hito[i:i+20] for i in range(0, len(hito), 20)]
    for i, line in enumerate(hito_lines[:2]):
        draw.text((10, 250 + i*25), line, font=font_item, fill=0)

    push_image(img, 4)

if __name__ == "__main__":
    # task_zhihu() # 知乎页面保持不变
    task_calendar()
    task_dashboard()
    print("全部执行完毕！")
