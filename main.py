import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

# 字体设置
FONT_PATH = "font.ttf"
try:
    font_title = ImageFont.truetype(FONT_PATH, 24)
    font_item = ImageFont.truetype(FONT_PATH, 18)
    font_small = ImageFont.truetype(FONT_PATH, 14)
    font_large = ImageFont.truetype(FONT_PATH, 40)
except:
    print("错误: 找不到 font.ttf")
    exit(1)

# ================= 绘图辅助函数 =================
def draw_newsnow_style_list(draw, title, items):
    draw.rounded_rectangle([(10, 10), (390, 45)], radius=8, fill=0)
    draw.text((20, 15), title, font=font_title, fill=255)
    
    y = 55
    for i, text in enumerate(items[:8]): 
        box_w, box_h = 24, 24
        draw.rounded_rectangle([(10, y), (10+box_w, y+box_h)], radius=6, fill=0)
        draw.text((16 if i<9 else 12, y+2), str(i+1), font=font_small, fill=255)
        
        if len(text) > 19:
            text = text[:18] + "..."
        draw.text((45, y+2), text, font=font_item, fill=0)
        y += 30

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

# ================= 页面 1：微博热搜 =================
def page1_weibo():
    print("获取微博热搜...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    items = []
    try:
        # 使用伪装成手机浏览器的请求头，绕过微博的服务器封锁
        mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*'
        }
        url = "https://m.weibo.cn/api/container/getIndex?containerid=106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot"
        res = requests.get(url, headers=mobile_headers, timeout=10).json()
        
        # 解析手机版返回的数据
        cards = res['data']['cards'][0]['card_group']
        for card in cards:
            if 'desc' in card:
                items.append(card['desc'])
    except Exception as e:
        print("微博获取报错:", e)
        items = ["获取微博数据失败，请检查接口..."] * 8
        
    draw_newsnow_style_list(draw, "🔥 微博实时热搜", items)
    push_image(img, page_id=1)

# ================= 页面 2：GitHub 趋势 =================
def page2_github():
    print("获取 GitHub 趋势...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    items = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = f"https://api.github.com/search/repositories?q=created:>{last_week}&sort=stars&order=desc"
        res = requests.get(url, headers=headers, timeout=10).json()
        for item in res['items'][:8]:
            items.append(f"{item['name']} ({item['stargazers_count']}★)")
    except Exception as e:
        print("GitHub获取报错:", e)
        items = ["获取数据失败..."] * 8
        
    draw_newsnow_style_list(draw, "💻 GitHub 热门开源", items)
    push_image(img, page_id=2)

# ================= 页面 3：综合看板 =================
def page3_dashboard():
    print("生成综合看板...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    # 1. 天气与智能穿衣建议
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "http://t.weather.itboy.net/api/weather/city/101030100"
        weather_data = requests.get(url, headers=headers, timeout=10).json()
        city = weather_data['cityInfo']['city']
        forecast = weather_data['data']['forecast'][0]
        wea = forecast['type']
        high_str = forecast['high'].replace('高温 ', '')
        low_str = forecast['low'].replace('低温 ', '')
        
        # 智能计算穿衣建议
        h_temp = int(high_str.replace('℃', ''))
        l_temp = int(low_str.replace('℃', ''))
        avg_temp = (h_temp + l_temp) / 2
        
        if avg_temp >= 28:
            tip = "天气炎热，建议穿短袖、短裤、裙子等清凉衣物。"
        elif avg_temp >= 20:
            tip = "体感舒适，建议穿单层薄外套、长袖衬衫、T恤。"
        elif avg_temp >= 14:
            tip = "天气微凉，建议穿风衣、夹克、薄毛衣、休闲装。"
        elif avg_temp >= 5:
            tip = "天气较冷，建议穿秋裤、厚毛衣、外套或薄羽绒服。"
        else:
            tip = "天气寒冷，请穿厚羽绒服、保暖内衣，注意防寒！"
    except Exception as e:
        print("天气获取报错:", e)
        city, wea, high_str, low_str = "天津", "未知", "0℃", "0℃"
        tip = "获取天气失败，请注意关注当地气温变化。"

    # 画左上角天气黑框
    draw.rounded_rectangle([(10, 10), (195, 120)], radius=10, fill=0)
    draw.text((20, 20), f"{city} | {wea}", font=font_title, fill=255)
    draw.text((20, 60), f"{low_str} ~ {high_str}", font=font_title, fill=255)
    
    # 2. 倒计时模块
    today = datetime.today().weekday()
    days_to_weekend = 5 - today
    if days_to_weekend <= 0:
        countdown_text = "已是周末!"
    else:
        countdown_text = f"还有 {days_to_weekend} 天"
        
    draw.rounded_rectangle([(205, 10), (390, 120)], radius=10, fill=0)
    draw.text((215, 20), "距离周末", font=font_item, fill=255)
    draw.text((215, 60), countdown_text, font=font_title, fill=255)

    # 3. 穿衣建议模块 (带自动折行)
    draw.text((10, 135), "👕 建议:", font=font_item, fill=0)
    tip_line1 = tip[:18]
    tip_line2 = tip[18:36] + "..." if len(tip) > 36 else tip[18:]
    draw.text((10, 160), tip_line1, font=font_item, fill=0)
    draw.text((10, 185), tip_line2, font=font_item, fill=0)

    # 4. 每日一言模块
    try:
        hitokoto = requests.get("https://v1.hitokoto.cn/?c=a", timeout=10).json()['hitokoto']
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
        print("错误: 请配置 GitHub Secrets")
        exit(1)
        
    page1_weibo()
    page2_github()
    page3_dashboard()
    print("全部执行完毕！")
