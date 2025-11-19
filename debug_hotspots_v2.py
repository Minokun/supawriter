import requests
import re

def test_weibo_scrape():
    print("Testing Weibo Scrape (s.weibo.com)...")
    url = "https://s.weibo.com/top/summary"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': 'SUB=_2AkMWJ_fdf8NxqwJRmP8SxWjnaY12yQ_EieKkjrMJJRMxHRl-yT9jqmgbtRB6PO6Nc9vS-pTH2Q7q8lW1D4q4e6P4' # Try a guest cookie or empty
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            # Look for <a href="/weibo?q=...">text</a>
            matches = re.findall(r'<a href="(/weibo\?q=[^"]+)"[^>]*>([^<]+)</a>', resp.text)
            # Filter out the "Refer" link usually at top
            real_hot = [m for m in matches if 'Refer=' not in m[0]]
            print(f"Found {len(real_hot)} items")
            for i, (link, title) in enumerate(real_hot[:5]):
                print(f"{i+1}. {title} -> {link}")
    except Exception as e:
        print(f"Error: {e}")

def test_36kr_scrape():
    print("\nTesting 36Kr Scrape (36kr.com/newsflashes)...")
    url = "https://36kr.com/newsflashes"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            # Regex to find initial state or directly parse HTML
            # Look for news item titles
            # <a class="item-title" ...>Title</a>
            matches = re.findall(r'<a[^>]+class="item-title"[^>]*>(.*?)</a>', resp.text)
            print(f"Found {len(matches)} titles via HTML regex")
            for t in matches[:5]:
                print(f"- {t}")
            
            # Also check if there is a script with state
            if "window.initialState" in resp.text:
                print("Found window.initialState")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_weibo_scrape()
    test_36kr_scrape()
