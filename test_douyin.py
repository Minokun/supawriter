import requests
import json

def test_douyin_hot():
    print("Testing Douyin Hot Search...")
    # Try the API endpoint often used
    url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.douyin.com/billboard/',
        'Cookie': 's_v_web_id=verify_ley4k77j_5L1r5q1L_5L1r_5L1r_5L1r_5L1r' # Random/Empty cookie might work or fail
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            word_list = data.get('data', {}).get('word_list', [])
            print(f"Found {len(word_list)} items")
            for item in word_list[:3]:
                print(f"- {item.get('word')} (Hot: {item.get('hot_value')})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_douyin_hot()
