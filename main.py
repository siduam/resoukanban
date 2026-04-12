import os
import requests
import calendar
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from zhdate import ZhDate

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

FONT_PATH = "font.ttf"
try:
    font_huge = ImageFont.truetype(FONT_PATH, 55)
    font_title = ImageFont.truetype(FONT_PATH, 24)
    font_item = ImageFont.truetype(FONT_PATH, 18)
    font_tiny = ImageFont.truetype(FONT_PATH, 11)
    font_small = ImageFont.truetype(FONT_PATH, 14)
except:
    print("错误: 找不到 font.ttf")
    exit(1)

# ================= 精确节气表 (2024-2027) =================
def get_accurate_solar_term(year, month, day):
    term_table = {
        (2024,4,4):"清明", (2024,5,5):"立夏", (2024,6,5):"芒种", (2024,6,21):"夏至", 
        (2024,7,6):"小暑", (2024,7,22):"大暑", (2024,8,7):"立秋", (2024,8,22):"处暑", 
        (2024,9,7):"白露", (2024,9,22):"秋分", (2024,10,8):"寒露", (2024,10,23):"霜降", 
        (2024,11,7):"立冬", (2024,11,22):"小雪", (2024,12,6):"大雪", (2024,12,21):"冬至",
        # 2025年
        (2025,1,5):"小寒", (2025,1,20):"大寒", (2025,2,3):"立春", (2025,2,18):"雨水",
        (2025,3,5):"惊蛰", (2025,3,20):"春分", (2025,4,4):"清明", (2025,4,20):"谷雨",
        (2025,5,5):"立夏", (2025,5,21):"小满", (2025,6,5):"芒种", (2025,6,21):"夏至",
        (2025,7,7):"小暑", (2025,7,22):"大暑", (2025,8,7):"立秋", (2025,8,23):"处暑",
        (2025,9,7):"白露", (2025,9,22):"秋分", (2025,10,8):"寒露", (2025,10,23):"霜降",
        (2025,11,7):"立冬", (2025,11,22):"小雪", (2025,12,7):"大雪", (2025,12,21):"冬至",
        # 2026年
        (2026,1,5):"小寒", (2026,1,20):"大寒", (2026,2,4):"立春", (2026,2,18):"雨水",
        (2026,3,5):"惊蛰", (2026,3,20):"春分", (2026,4,5):"清明", (2026,4,20):"谷雨",
        (2026,5,5):"立夏", (2026,5,21):"小满", (2026,6,6):"芒种", (2026,6,21):"夏至",
    }
    return term_table.get((year, month, day), None)

def get_lunar_or_term(y, m, d):
    """返回日历下方的文字：节气 > 节日 > 农历"""
    # 1. 节气优先
    term = get_accurate_solar_term(y, m, d)
    if term: return term
    
    # 2. 阳历节日
    fests = {(1,1):"元旦", (2,14):"情人节", (3,8):"妇女节", (5,1):"劳动节", 
             (6,1):"儿童节", (10,1):"国庆节", (12,25):"圣诞节"}
    if (m, d) in fests: return fests[(m, d)]
    
    # 3. 农历及农历节日
    try:
        lunar = ZhDate.from_datetime(datetime(y, m, d))
        lm, ld = lunar.lunar_month, lunar.lunar_day
        l_fests = {(1,1):"春节", (1,15):"元宵", (5,5):"端午", (7,7):"七夕", 
                   (8,15):"中秋", (9,9):"重阳", (12,30):"除夕"}
        if (lm, ld) in l_fests: return l_fests[(lm, ld)]
        
        # 转换农历数字为中文
        days = ["初一","初二","初三","初四","初五","初六","初七","初八","初九","初十",
                "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
                "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"]
        months = ["正月","二月","三月","四月","五月","六月","七月","八月","九月","十月","冬月","腊月"]
        if ld == 1:
            return months[lm-1] # 初一显示月份
        return days[ld-1]
    except:
        return ""

# ================= 免Key获取全球天气 =================
def get_free_weather():
    try:
        # 使用 wttr.in 免费接口，极度稳定，不封号
        url = "https://wttr.in/Tianjin?format=j1&lang=zh"
        resp = requests.get(url, timeout=10).json()
        
        curr = resp['current_condition'][0]
        today = resp['weather'][0]
        
        weather_text = curr['lang_zh'][0]['value']
        temp_min = today['mintempC']
        temp_max = today['maxtempC']
        
        hours, temps = [], []
        # 提取每3小时的温度用于画折线图
        for h in today['hourly']:
            hour = int(h['time']) // 100
            temp = int(h['tempC'])
            hours.append(hour)
            temps.append(temp)
            
        return "津南区", weather_text, temp_min, temp_max, (hours, temps)
    except Exception as e:
        print(f"天气接口异常: {e}")
        return None

def draw_temp_curve(draw, hours, temps, x0, y0, width, height):
    """绘制温度折线图"""
    if not hours or len(temps) < 2:
        draw.text((x0, y0), "数据获取中...", font=font_item, fill=0)
        return
    x_step = width / (len(hours)-1)
    y_min, y_max = min(temps), max(temps)
    y_range = max(y_max - y_min, 1)
    
    points = []
    for i, (h, t) in enumerate(zip(hours, temps)):
        x = x0 + i * x_step
        y = y0 + height - (t - y_min) / y_range * height
        points.append((x, y))
        
    draw.line(points, fill=0, width=2)
    draw.text((x0, y0-16), f"{temps[0]}℃", font=font_tiny, fill=0)
    draw.text((x0+width-20, y0-16), f"{temps[-1]}℃", font=font_tiny, fill=0)
    
    # 底部标明时间
    for i in range(len(hours)):
        x = x0 + i * x_step
        draw.text((x-6, y0+height+4), f"{hours[i]}h", font=font_tiny, fill=0)

# ================= 推送图片 =================
def push_image(img, page_id):
    img.save(f"page_{page_id}.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": (f"page_{page_id}.png", open(f"page_{page_id}.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    requests.post(PUSH_URL, headers=api_headers, files=files, data=data)

# ================= Page 3: 日历 =================
def task_calendar():
    print("生成 Page 3: 实体台历...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)

    now = datetime.now()
    y, m, today = now.year, now.month, now.day

    draw.text((20, 10), str(m), font=font_huge, fill=0)
    draw.text((85, 20), now.strftime("%B"), font=font_title, fill=0)
    draw.text((85, 48), str(y), font=font_item, fill=0)
    draw.line([(20, 78), (380, 78)], fill=0, width=2)

    headers = ["日", "一", "二", "三", "四", "五", "六"]
    col_w = 53
    for i, h in enumerate(headers):
        draw.text((25 + i*col_w, 88), h, font=font_small, fill=0)

    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(y, m)
    curr_y = 115
    row_h = 36

    for week in cal:
        for c, day in enumerate(week):
            if day != 0:
                dx = 25 + c * col_w
                if day == today:
                    draw.rounded_rectangle([(dx-3, curr_y-2), (dx+32, curr_y+32)], radius=5, outline=0)

                # 阳历数字
                draw.text((dx+2, curr_y), str(day), font=font_item, fill=0)

                # 农历文字
                bottom_text = get_lunar_or_term(y, m, day)
                if bottom_text:
                    # 如果字数太长(比如劳动节)，缩小字体
                    if len(bottom_text) >= 3:
                        draw.text((dx-1, curr_y+18), bottom_text, font=font_tiny, fill=0)
                    else:
                        draw.text((dx+2, curr_y+18), bottom_text, font=font_tiny, fill=0)
        curr_y += row_h

    push_image(img, 3)

# ================= Page 4: 综合看板 =================
def task_dashboard():
    print("生成 Page 4: 综合看板...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)

    weather = get_free_weather()
    if weather:
        city_name, weather_text, temp_min, temp_max, hourly_data = weather
        title_str = f"{city_name} | {weather_text}"
        temp_range = f"{temp_min}℃ ~ {temp_max}℃"
    else:
        title_str = "津南区 | 天气获取失败"
        temp_range = "请检查网络"
        hourly_data = None

    # 左侧天气
    draw.rounded_rectangle([(10, 10), (195, 120)], radius=10, fill=0)
    draw.text((20, 20), title_str, font=font_title, fill=255)
    draw.text((20, 60), temp_range, font=font_title, fill=255)

    # 右侧倒计时
    days = 5 - datetime.today().weekday()
    draw.rounded_rectangle([(205, 10), (390, 120)], radius=10, fill=0)
    draw.text((215, 20), "距离周末", font=font_item, fill=255)
    draw.text((215, 60), "已是周末!" if days <= 0 else f"还有 {days} 天", font=font_title, fill=255)

    # 温度曲线
    draw.text((10, 135), "📈 今日气温走势", font=font_item, fill=0)
    if hourly_data:
        hours, temps = hourly_data
        draw_temp_curve(draw, hours, temps, 15, 160, 370, 45)

    # 每日一言
    try:
        hito = requests.get("https://v1.hitokoto.cn/?c=i", timeout=5).json()['hitokoto']
    except:
        hito = "实事求是。"
    draw.line([(10, 225), (390, 225)], fill=0, width=2)
    draw.text((10, 235), "「每日一言」", font=font_small, fill=0)
    hito_lines = [hito[i:i+20] for i in range(0, len(hito), 20)]
    for i, line in enumerate(hito_lines[:2]):
        draw.text((10, 255 + i*25), line, font=font_item, fill=0)

    push_image(img, 4)

if __name__ == "__main__":
    task_calendar()
    task_dashboard()
    print("全部执行完毕！")
