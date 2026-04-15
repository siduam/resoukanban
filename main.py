import os
import requests
import calendar
import re
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from zhdate import ZhDate

# =====================================================================
# 🌟 第一部分：用户自定义区（想改什么，直接在这里改文字和数字） 🌟
# =====================================================================

# 1. 控制推送哪几页？
ENABLED_PAGES = "1,2,3,4"

# 2. 热搜源设置：支持 'zhihu', 'bilibili', 'github', 'thepaper', 'quote', 'history'
HOTLIST_SOURCE = "history"  # 在这里修改你想看的热搜源

# 3. 天气城市设置
CITY_ADCODE = "120112"                      
WTTR_LOCATION = "Jinnan,Tianjin"            

# 4. 屏幕显示文字
CITY_DISPLAY_NAME = "津南区 | 天大北洋园"      

# =====================================================================
# 🔒 第二部分：核心密钥区（⚠️绝对不要改这里） 🔒
# =====================================================================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
AMAP_KEY = os.environ.get("AMAP_WEATHER_KEY")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

# =====================================================================
# ⚙️ 第三部分：底层运行逻辑（如果没有报错，不需要修改以下代码） ⚙️
# =====================================================================

# --- 字体设置 ---
FONT_PATH = "font.ttf"
try:
    font_huge = ImageFont.truetype(FONT_PATH, 65)
    font_title = ImageFont.truetype(FONT_PATH, 24)
    font_item = ImageFont.truetype(FONT_PATH, 18)
    font_small = ImageFont.truetype(FONT_PATH, 14)
    font_tiny = ImageFont.truetype(FONT_PATH, 11)
    font_48 = ImageFont.truetype(FONT_PATH, 48)
    font_36 = ImageFont.truetype(FONT_PATH, 36)
except:
    print("❌ 错误: 找不到 font.ttf")
    exit(1)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# --- 获取热搜数据的通用逻辑 ---
def get_hotlist_data(source):
    titles = []
    print(f"正在从 {source} 获取热搜数据...")
    try:
        if source == "zhihu":
            url = "https://api.zhihu.com/topstory/hot-list"
            res = requests.get(url, headers=HEADERS, timeout=10).json()
            titles = [item['target']['title'] for item in res['data']]
        elif source == "bilibili":
            url = "https://api.bilibili.com/x/web-interface/wbi/search/square?limit=20"
            res = requests.get(url, headers=HEADERS, timeout=10).json()
            titles = [item['show_name'] for item in res['data']['trending']['list']]
        elif source == "github":
            url = "https://api.github.com/search/repositories?q=created:%3E" + (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d') + "&sort=stars&order=desc"
            res = requests.get(url, headers=HEADERS, timeout=10).json()
            titles = [f"{item['full_name']}: {item['description'][:40] if item['description'] else 'No desc'}" for item in res['items']]
        elif source == "thepaper":
            # 澎湃新闻头条
            url = "https://www.thepaper.cn/content-api/content/publish/home/list"
            res = requests.get(url, headers=HEADERS, timeout=10).json()
            titles = [item['name'] for item in res['data']['list']]
        elif source == "quote":
            # 每日一句 (使用金山词霸/随机名言接口)
            url = "http://open.iciba.com/dsapi/"
            res = requests.get(url, headers=HEADERS, timeout=10).json()
            titles = [res['content'], res['note'], "—— 今日名言 ——"]
        elif source == "history":
            # 历史上的今天
            m, d = datetime.now().month, datetime.now().day
            url = f"https://baike.baidu.com/cms/home/eventsOnHistory/{m:02d}.json"
            res = requests.get(url, headers=HEADERS, timeout=10).json()
            raw_data = res.get(f"{m:02d}", {}).get(f"{m:02d}{d:02d}", [])
            titles = [re.sub(r'<[^>]+>', '', item['title']) for item in raw_data[::-1]]
        else:
            titles = ["不支持的数据源"]
    except Exception as e:
        print(f"获取热搜失败 ({source}): {e}")
        titles = ["数据获取失败，请检查网络或配置"] * 10
    return titles[:20]

# --- 工具函数 ---
def get_wrapped_lines(text, max_chars=18):
    lines = []
    while text:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    return lines

def get_clothing_advice(temp):
    try:
        t = int(temp)
        if t >= 28: return "建议穿短袖、短裤，注意防晒补水。"
        elif t >= 22: return "体感舒适，建议穿 T 恤配薄长裤。"
        elif t >= 16: return "建议穿长袖衬衫、卫衣或单层薄外套。"
        elif t >= 10: return "气温微凉，建议穿夹克、风衣或毛衣。"
        elif t >= 5: return "建议穿大衣、厚毛衣或薄款羽绒服。"
        else: return "天气寒冷，建议穿厚羽绒服，注意防寒。"
    except: return "请根据体感气温调整。"

def push_image(img, page_id):
    if str(page_id) not in ENABLED_PAGES: return
    img.save(f"page_{page_id}.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": (f"page_{page_id}.png", open(f"page_{page_id}.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    try:
        res = requests.post(PUSH_URL, headers=api_headers, files=files, data=data)
        print(f"✅ Page {page_id} 推送成功")
    except Exception as e: print(f"❌ Page {page_id} 推送失败: {e}")

# --- 节气与农历 (保持不变) ---
def get_solar_term(year, month, day):
    term_table = {(2024,2,4):"立春", (2024,2,19):"雨水", (2024,3,5):"惊蛰", (2024,3,20):"春分", (2024,4,4):"清明", (2024,4,19):"谷雨", (2024,5,5):"立夏", (2024,5,20):"小满", (2024,6,5):"芒种", (2024,6,21):"夏至", (2024,7,6):"小暑", (2024,7,22):"大暑", (2024,8,7):"立秋", (2024,8,22):"处暑", (2024,9,7):"白露", (2024,9,22):"秋分", (2024,10,8):"寒露", (2024,10,23):"霜降", (2024,11,7):"立冬", (2024,11,22):"小雪", (2024,12,6):"大雪", (2024,12,21):"冬至", (2025,1,5):"小寒", (2025,1,20):"大寒", (2025,2,3):"立春", (2025,2,18):"雨水", (2025,3,5):"惊蛰", (2025,3,20):"春分", (2025,4,4):"清明", (2025,4,20):"谷雨", (2025,5,5):"立夏", (2025,5,21):"小满", (2025,6,5):"芒种", (2025,6,21):"夏至", (2025,7,7):"小暑", (2025,7,22):"大暑", (2025,8,7):"立秋", (2025,8,23):"处暑", (2025,9,7):"白露", (2025,9,22):"秋分", (2025,10,8):"寒露", (2025,10,23):"霜降", (2025,11,7):"立冬", (2025,11,22):"小雪", (2025,12,7):"大雪", (2025,12,21):"冬至", (2026,1,5):"小寒", (2026,1,20):"大寒", (2026,2,4):"立春", (2026,2,18):"雨水", (2026,3,5):"惊蛰", (2026,3,20):"春分", (2026,4,5):"清明", (2026,4,20):"谷雨", (2026,5,5):"立夏", (2026,5,21):"小满", (2026,6,6):"芒种", (2026,6,21):"夏至", (2026,7,7):"小暑", (2026,7,23):"大暑", (2026,8,7):"立秋", (2026,8,23):"处暑", (2026,9,7):"白露", (2026,9,23):"秋分", (2026,10,8):"寒露", (2026,10,23):"霜降", (2026,11,7):"立冬", (2026,11,22):"小雪", (2026,12,7):"大雪", (2026,12,21):"冬至", (2027,1,5):"小寒", (2027,1,20):"大寒", (2027,2,4):"立春", (2027,2,19):"雨水", (2027,3,6):"惊蛰", (2027,3,21):"春分", (2027,4,5):"清明", (2027,4,20):"谷雨"}
    return term_table.get((year, month, day), None)

def get_lunar_or_festival(y, m, d):
    term = get_solar_term(y, m, d)
    if term: return term
    solar_fests = {(1,1):"元旦", (2,14):"情人节", (3,8):"妇女节", (4,1):"愚人节", (5,1):"劳动节", (6,1):"儿童节", (7,1):"建党节", (8,1):"建军节", (9,10):"教师节", (10,1):"国庆节", (12,25):"圣诞节"}
    if (m, d) in solar_fests: return solar_fests[(m, d)]
    try:
        lunar = ZhDate.from_datetime(datetime(y, m, d))
        lm, ld = lunar.lunar_month, lunar.lunar_day
        lunar_fests = {(1,1):"春节", (1,15):"元宵节", (5,5):"端午节", (7,7):"七夕节", (8,15):"中秋节", (9,9):"重阳节", (12,30):"除夕"}
        if (lm, ld) in lunar_fests: return lunar_fests[(lm, ld)]
        days = ["初一","初二","初三","初四","初五","初六","初七","初八","初九","初十", "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十", "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"]
        months = ["正月","二月","三月","四月","五月","六月","七月","八月","九月","十月","冬月","腊月"]
        return months[lm-1] if ld == 1 else days[ld-1]
    except: return ""

# --- 绘制热搜任务 (UI 逻辑不变) ---
def task_hotlist():
    source_map = {"zhihu": "知乎热榜", "bilibili": "B站热搜", "github": "GitHub 热门", "thepaper": "澎湃新闻头条", "quote": "每日名言金句", "history": "历史上的今天"}
    titles = get_hotlist_data(HOTLIST_SOURCE)
    title_display = source_map.get(HOTLIST_SOURCE, "热门资讯")

    def draw_list(draw, page_title, items, start_idx):
        draw.rounded_rectangle([(10, 10), (390, 45)], radius=8, fill=0)
        draw.text((20, 15), page_title, font=font_title, fill=255)
        y, last_idx = 55, start_idx
        item_gap, line_height = 12, 22
        for i in range(start_idx, len(items)):
            lines = get_wrapped_lines(items[i], 19)
            required_h = len(lines) * line_height
            if y + required_h > 295: break
            current_num = i + 1
            draw.rounded_rectangle([(10, y), (36, y+24)], radius=6, fill=0)
            num_x = 18 if current_num < 10 else 11
            draw.text((num_x, y+2), str(current_num), font=font_small, fill=255)
            curr_y = y + 2
            for line in lines:
                draw.text((45, curr_y), line, font=font_item, fill=0)
                curr_y += line_height
            y += max(24, required_h) + item_gap
            last_idx = i + 1
            if y < 290: draw.line([(45, y - item_gap/2), (380, y - item_gap/2)], fill=0, width=1)
        return last_idx

    if "1" in ENABLED_PAGES:
        img1 = Image.new('1', (400, 300), color=255)
        next_s = draw_list(ImageDraw.Draw(img1), f"◆ {title_display} (一)", titles, 0)
        push_image(img1, 1)
    else: next_s = 7 

    if "2" in ENABLED_PAGES:
        img2 = Image.new('1', (400, 300), color=255)
        draw_list(ImageDraw.Draw(img2), f"◆ {title_display} (二)", titles, next_s)
        push_image(img2, 2)

# --- 绘制日历任务 (保持不变) ---
def task_calendar():
    if "3" not in ENABLED_PAGES: return
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    now = (datetime.utcnow() + timedelta(hours=8))
    y, m, today = now.year, now.month, now.day
    draw.text((20, 10), str(m), font=font_huge, fill=0)
    draw.text((90, 20), now.strftime("%B"), font=font_title, fill=0)
    draw.text((90, 48), str(y), font=font_item, fill=0)
    draw.line([(20, 78), (380, 78)], fill=0, width=2)
    headers = ["日", "一", "二", "三", "四", "五", "六"]
    for i, h in enumerate(headers): draw.text((25 + i*53, 88), h, font=font_small, fill=0)
    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(y, m)
    curr_y = 115
    for week in cal:
        for c, day in enumerate(week):
            if day != 0:
                dx = 25 + c * 53
                if day == today: draw.rounded_rectangle([(dx-3, curr_y-2), (dx+35, curr_y+32)], radius=5, outline=0)
                draw.text((dx+2, curr_y), str(day), font=font_item, fill=0)
                btm = get_lunar_or_festival(y, m, day)
                if btm: draw.text((dx+2, curr_y+18), btm[:3], font=font_tiny, fill=0)
        curr_y += 38
    push_image(img, 3)

# --- 绘制天气任务 (保持不变) ---
def task_weather_dashboard():
    if "4" not in ENABLED_PAGES: return
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    def fetch():
        res = {"city": CITY_DISPLAY_NAME.split("|")[0].strip(), "weather": "未知", "temp_curr": 0, "temp_low": 0, "temp_high": 0, "wind_info": "无数据", "humidity": "0%", "feel_temp": "N/A", "sunrise": "--:--", "sunset": "--:--", "forecasts": []}
        try:
            live = requests.get(f"https://restapi.amap.com/v3/weather/weatherInfo?city={CITY_ADCODE}&key={AMAP_KEY}&extensions=base", timeout=10).json()["lives"][0]
            res.update({"weather": live["weather"], "temp_curr": int(live["temperature"]), "humidity": live["humidity"]+"%", "wind_info": f"{live['windpower']}级 {live['winddirection']}"})
            casts = requests.get(f"https://restapi.amap.com/v3/weather/weatherInfo?city={CITY_ADCODE}&key={AMAP_KEY}&extensions=all", timeout=10).json()["forecasts"][0]["casts"]
            res.update({"temp_low": int(casts[0]["nighttemp"]), "temp_high": int(casts[0]["daytemp"])})
            for d in casts[1:3]: res["forecasts"].append({"date": d["date"][5:], "weather": d["dayweather"], "temp_low": int(d["nighttemp"]), "temp_high": int(d["daytemp"])})
            wttr = requests.get(f"https://wttr.in/{WTTR_LOCATION}?format=j1&lang=zh", timeout=15).json()["weather"][0]["astronomy"][0]
            res.update({"sunrise": wttr["sunrise"], "sunset": wttr["sunset"]})
        except: pass
        return res
    w = fetch()
    draw.text((20, 10), CITY_DISPLAY_NAME, font=font_title, fill=0)
    draw.text((310, 12), f"更新: {(datetime.utcnow()+timedelta(hours=8)).strftime('%H:%M')}", font=font_small, fill=0)
    draw.text((25, 40), f"{w['temp_curr']}°C", font=font_48, fill=0)
    draw.text((150, 45), w['weather'], font=font_36, fill=0)
    draw.rounded_rectangle([(235, 45), (385, 130)], radius=8, outline=0, fill=0)
    draw.text((245, 45), w['wind_info'], font=font_small, fill=255)
    draw.text((245, 70), f"湿度 {w['humidity']}", font=font_small, fill=255)
    draw.text((25, 135), f"日出 {w['sunrise']}   日落 {w['sunset']}", font=font_item, fill=0)
    draw.line([(20, 160), (380, 160)], fill=0, width=1)
    for i, d in enumerate(w['forecasts']): draw.text((30+i*170, 175), f"{d['date']} {d['weather']} {d['temp_low']}°~{d['temp_high']}°", font=font_item, fill=0)
    adv = get_clothing_advice(w['temp_curr'])
    draw.text((20, 262), f"[衣] {adv[:18]}", font=font_item, fill=0)
    push_image(img, 4)

# ================= 主程序 =================
if __name__ == "__main__":
    if not API_KEY or not MAC_ADDRESS: exit(1)
    task_hotlist()
    task_calendar()
    task_weather_dashboard()
