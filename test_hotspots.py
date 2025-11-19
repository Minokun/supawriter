import requests
import json
import time

def test_36kr():
    url = "https://gateway.36kr.com/api/mis/nav/newsflash/flow"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json'
    }
    payload = {
        "partner_id": "web",
        "timestamp": int(time.time() * 1000),
        "param": {
            "pageSize": 20,
            "pageEvent": 0,
            "pageCallback": ""
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"36Kr Status: {resp.status_code}")
        if resp.status_code == 200:
            print(str(resp.json())[:200])
    except Exception as e:
        print(f"36Kr Error: {e}")

def test_baidu():
    url = "https://top.baidu.com/board?tab=realtime"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Baidu Status: {resp.status_code}")
        if "百度热搜" in resp.text:
            print("Baidu content found")
    except Exception as e:
        print(f"Baidu Error: {e}")

if __name__ == "__main__":
    test_36kr()
    test_baidu()
