import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

with open('article_ids.txt', 'r') as file:
    article_ids = [line.strip() for line in file]

base_url = "https://digmee.jp/article/"
article_urls = [f"{base_url}{article_id}" for article_id in article_ids]

broken_links_by_domain = {}

progress_counter = 0
total_articles = len(article_urls)
progress_lock = threading.Lock()  

def check_links(article_url):
    global progress_counter
    try:
        response = requests.get(article_url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        links = soup.find_all('a')

        for link in links:
            href = link.get('href')
            if href and 'twitter.com/intent/tweet' not in href and not href.startswith('#') and href != "https://digmee.jp":
                if href.startswith('/') or href.startswith('javascript'):
                    continue  

                try:
                    res = requests.get(href, timeout=5)
                    if 400 <= res.status_code < 500:  
                        domain = urlparse(href).netloc
                        if domain not in broken_links_by_domain:
                            broken_links_by_domain[domain] = []
                        broken_links_by_domain[domain].append((href, res.status_code, article_url))  
                except requests.RequestException:
                    domain = urlparse(href).netloc
                    if domain not in broken_links_by_domain:
                        broken_links_by_domain[domain] = []
                    broken_links_by_domain[domain].append((href, "Request Error", article_url))

    except requests.RequestException as e:
        print(f"記事にアクセスできませんでした: {article_url}, エラー: {e}")

    with progress_lock:
        progress_counter += 1
        print(f"進捗: {progress_counter}/{total_articles}")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(check_links, url) for url in article_urls]

    for future in as_completed(futures):
        future.result()  

for domain, links in broken_links_by_domain.items():
    print(f"\nドメイン: {domain}")
    for href, status_code, article_url in links:
        print(f"  切れているURL: {href} (ステータスコード: {status_code}) - 元記事: {article_url}")
