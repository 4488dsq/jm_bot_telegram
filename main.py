import os
import jmcomic
import requests
import shutil
import time
import random

# 从环境变量读取 Secrets
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
    # 1. 确保账本文件存在
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, 'w').close()
    
    with open(HISTORY_FILE, 'r') as f:
        history = set(line.strip() for line in f if line.strip())

    # 2. 初始化 JmComic
    option = jmcomic.JmOption.default()
    option.dir_rule.base_dir = './output'
    client = option.new_jm_client()
    
    keywords = ['催眠', '超能力']
    count = 0
    max_per_day = 30 # 每天稳稳下载 30 本，不急不躁

    for kw in keywords:
        if count >= max_per_day: break
        print(f"🔎 正在扫描关键词: {kw}")
        
        # 爬取前 3 页即可，因为每天都跑，新出的总会被抓到
        for page in range(1, 4):
            if count >= max_per_day: break
            search_page = client.search_site(search_query=kw, page=page)
            
            for album in search_page.content:
                aid = str(album.id)
                if aid in history: continue
                
                print(f"🚀 开始搬运: {album.title}")
                try:
                    # 下载
                    jmcomic.download_album(aid, option)
                    # 寻找下载目录
                    album_path = os.path.join('./output', aid)
                    if not os.path.exists(album_path): album_path = os.path.join('./output', album.title)
                    
                    # 压缩
                    os.makedirs('./zips', exist_ok=True)
                    zip_path = shutil.make_archive(f'./zips/{aid}', 'zip', album_path)
                    
                    # 发送 (限制 50MB)
                    if os.path.getsize(zip_path) < 49 * 1024 * 1024:
                        if send_to_tg(zip_path, f"【{kw}】{album.title}\nID: {aid}"):
                            # 记录成功
                            with open(HISTORY_FILE, 'a') as f:
                                f.write(f"{aid}\n")
                            count += 1
                            print(f"✅ 已完成: {count}/{max_per_day}")
                    else:
                        print(f"⚠️ {aid} 超过50MB，跳过发送")
                    
                    # 彻底删除，释放 Actions 空间
                    shutil.rmtree(album_path, ignore_errors=True)
                    if os.path.exists(zip_path): os.remove(zip_path)
                    
                    # 随机休眠，保护 IP
                    time.sleep(random.uniform(5, 10))
                    
                except Exception as e:
                    print(f"❌ 下载失败 {aid}: {e}")

if __name__ == '__main__':
    run()