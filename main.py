import os
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

FONT_PATH = "font.ttf"
try:
    font_title = ImageFont.truetype(FONT_PATH, 24) # 标题
    font_item = ImageFont.truetype(FONT_PATH, 18)  # 正文
    font_small = ImageFont.truetype(FONT_PATH, 14) # 序号/小字
except:
    print("错误: 找不到 font.ttf")
    exit(1)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ================= 核心绘图函数 (支持自动换行) =================
def draw_wrapped_list(draw, page_title, items, start_num=1):
    """
    items: 字符串列表
    start_num: 起始序号
    """
    # 1. 绘制黑底白字页眉
    draw.rounded_rectangle([(10, 5), (390, 40)], radius=8, fill=0)
    draw.text((20, 8), page_title, font=font_title, fill=255)
    
    y = 55
    line_height = 22 # 单行文字高度
    item_gap = 12   # 条目间距
    
    for i, text in enumerate(items):
        # 使用 textwrap 自动换行，每行约 18 个汉字
        lines = textwrap.wrap(text, width=18)
        
        # 2. 绘制序号方块 (只在第一行左侧)
        box_size = 24
        draw.rounded_rectangle([(10, y), (10 + box_size, y + box_size)], radius=6, fill=0)
        draw.text((15 if (i+start_num)<10 else 11, y+2), str(i+start_num), font=font_small, fill=255)
        
        # 3. 逐行绘制标题文字
        current_y = y + 2
        for line in lines:
            if current_y > 280: break # 防止超出屏幕
            draw.text((45, current_y), line, font=font_item, fill=0)
            current_y += line_height
            
        # 4. 计算下一条的起始位置 (根据实际行数动态调整)
        # 确保下一条至少在序号框下面，或者是文字末尾下面
        occupied_height = max(box_size, (len(lines) * line_height))
        y += occupied_height + item_gap
        
        # 画一条浅浅的分隔线
        if i < len(items) - 1 and y < 290:
            draw.line([(45, y - item_gap/2), (380, y - item_gap/2)], fill=0, width=1)

def push_image(img, page_id):
    img.save(f"page_{page_id}.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": (f"page_{page_id}.png", open(f"page_{page_id}.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    try:
        res = requests.post(PUSH_URL, headers=api_headers, files=files, data=data)
        print(f"Page {page_id} 推送状态:", res.status_code)
    except Exception as e:
        print(f"Page {page_id} 推送失败:", e)

# ================= 页面 1 & 2：知乎热榜 =================
def fetch_zhihu_and_push():
    print("正在获取知乎热榜...")
    try:
        url = "https://api.zhihu.com/topstory/hot-list"
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        all_titles = [item['target']['title'] for item in res['data']]
    except Exception as e:
        print("知乎获取失败:", e)
        all_titles = ["获取失败，请检查网络"] * 10

    # 页面 1 (1-5名)
    img1 = Image.new('1', (400, 300), color=255)
    draw_wrapped_list(ImageDraw.Draw(img1), "🔥 知乎热榜 (1-5)", all_titles[0:5], start_num=1)
    push_image(img1, page_id=1)

    # 页面 2 (6-10名)
    img2 = Image.new('1', (400, 300), color=255)
    draw_wrapped_list(ImageDraw.Draw(img2), "🔥 知乎热榜 (6-10)", all_titles[5:10], start_num=6)
    push_image(img2, page_id=2)

# ================= 页面 3：GitHub 趋势 =================
def page3_github():
    print("获取 GitHub 趋势...")
    items = []
    try:
        gh_headers = HEADERS.copy()
        if GITHUB_TOKEN: gh_headers['Authorization'] = f"token {GITHUB_TOKEN}"
        last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = f"https://api.github.com/search/repositories?q=created:>{last_week}&sort=stars&order=desc"
        res = requests.get(url, headers=gh_headers, timeout=10).json()
        for item in res['items'][:6]: # GitHub 标题通常较短，可以放 6 条
            items.append(f"{item['name']} ({item['stargazers_count']}★)")
    except:
        items = ["获取数据失败"] * 5
        
    img = Image.new('1', (400, 300), color=255)
    draw_wrapped_list(ImageDraw.Draw(img), "💻 GitHub 热门项目", items)
    push_image(img, page_id=3)

# ================= 页面 4：综合看板 (天气+金句) =================
def page4_dashboard():
    print("生成综合看板...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    # 顶部日期栏
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d  %A")
    draw.rounded_rectangle([(10, 5), (390, 40)], radius=8, fill=0)
    draw.text((20, 8), f"📅 {date_str}", font=font_title, fill=255)

    # 天气区块
    try:
        url = "http://t.weather.itboy.net/api/weather/city/101030100" # 天津代码
        weather = requests.get(url, headers=HEADERS, timeout=10).json()
        data = weather['data']['forecast'][0]
        weather_text = f"{weather['cityInfo']['city']}：{data['type']}  {data['low']}~{data['high']}"
        notice = data['notice']
    except:
        weather_text, notice = "天气获取失败", "请注意增减衣物"

    draw.text((15, 60), weather_text, font=font_item, fill=0)
    # 自动换行显示气象提醒
    notice_lines = textwrap.wrap(f"提醒：{notice}", width=20)
    for i, line in enumerate(notice_lines):
        draw.text((15, 90 + i*22), line, font=font_item, fill=0)

    # 每日一言区块
    try:
        hitokoto = requests.get("https://v1.hitokoto.cn/?c=i", timeout=10).json()['hitokoto']
    except:
        hitokoto = "永远年轻，永远热泪盈眶。"
        
    draw.line([(10, 160), (390, 160)], fill=0, width=2)
    draw.text((15, 175), "「 每日一言 」", font=font_item, fill=0)
    
    # 金句自动换行显示在底部
    hito_lines = textwrap.wrap(hitokoto, width=19)
    for i, line in enumerate(hito_lines):
        draw.text((15, 205 + i*25), line, font=font_item, fill=0)

    push_image(img, page_id=4)

# ================= 页面 5：自定义展示 =================
def page5_custom():
    print("生成自定义页面...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(10, 5), (390, 40)], radius=8, fill=0)
    draw.text((20, 8), "✨ 自定义展示区", font=font_title, fill=255)
    
    # 你可以在这里放：股票行情、待办清单、或者一张图
    msg = "这里是预留空间\n\n你可以修改代码\n显示你的 Todo List\n或者个人座右铭。"
    draw.multiline_text((50, 100), msg, font=font_item, fill=0, spacing=10)
    
    push_image(img, page_id=5)

# ================= 执行 =================
if __name__ == "__main__":
    if not API_KEY or not MAC_ADDRESS:
        print("错误: 请在 GitHub Secrets 中配置 API_KEY 和 MAC")
        exit(1)
        
    fetch_zhihu_and_push() # 处理 Page 1 和 2
    page3_github()         # 处理 Page 3
    page4_dashboard()      # 处理 Page 4
    page5_custom()         # 处理 Page 5
    print("所有页面推送完成！")
