import os
import jmcomic
import requests
import shutil
import time
import random

# --- 配置 ---
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
HISTORY_FILE = 'downloaded_ids.txt'

def send_to_tg(file_path, caption):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            res = requests.post(url, data={'chat_id': TG_CHAT_ID, 'caption': caption}, files={'document': f}, timeout=120)
        return res.status_code == 200
    except:
        return False

def run():
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, 'w').close()
    
    with open(HISTORY_FILE, 'r') as f:
        history = set(line.strip() for line in f if line.strip())

    # 配置：强制切换到 HTML 模式，API 模式有时会报数据库错误
    option = jmcomic.JmOption.default()
    option.client.impl = 'html' # 切换为 html 模式更稳定
    option.dir_rule.base_dir = './output'
    client = option.new_jm_client()
    
    keywords = ['催眠', '超能力']
    count = 0
    max_per_day = 20 # 建议先从 20 本开始

    for kw in keywords:
        if count >= max_per_day: break
        print(f"🔎 正在扫描关键词: {kw}")
        
        for page in range(1, 3):
            if count >= max_per_day: break
            
            try:
                # 修复元组解包问题
                search_result = client.search_site(search_query=kw, page=page)
                
                # 如果返回的是元组 (content, total)，取第一个
                if isinstance(search_result, tuple):
                    album_list = search_result[0]
                else:
                    album_list = search_result.content

                for album in album_list:
                    aid = str(album.id)
                    if aid in history: continue
                    
                    print(f"🚀 发现新本: [{aid}] {album.title}")
                    
                    # 下载
                    jmcomic.download_album(aid, option)
                    
                    # 确定路径 (有些系统路径包含 Aid，有些包含 Title)
                    album_path = os.path.join('./output', aid)
                    if not os.path.exists(album_path):
                        album_path = os.path.join('./output', album.title)
                    
                    # 压缩
                    os.makedirs('./zips', exist_ok=True)
                    zip_path = shutil.make_archive(os.path.join('./zips', aid), 'zip', album_path)
                    
                    # 发送
                    if os.path.getsize(zip_path) < 49 * 1024 * 1024:
                        if send_to_tg(zip_path, f"【{kw}】{album.title}\nID: {aid}"):
                            with open(HISTORY_FILE, 'a') as f:
                                f.write(f"{aid}\n")
                            count += 1
                            print(f"✅ 完成进度: {count}/{max_per_day}")
                    else:
                        print(f"⚠️ {aid} 过大，跳过发送")
                    
                    # 清理空间
                    shutil.rmtree(album_path, ignore_errors=True)
                    if os.path.exists(zip_path): os.remove(zip_path)
                    
                    time.sleep(random.uniform(3, 7))
                    
            except Exception as e:
                print(f"❌ 处理关键词 {kw} 时出错: {e}")
                continue

if __name__ == '__main__':
    run()
