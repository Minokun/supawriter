import requests
import json

print("=" * 80)
print("1. 测试机器之心API")
print("=" * 80)
try:
    url = "https://www.jiqizhixin.com/api/article_library/articles.json?sort=time&page=1&per=12"
    response = requests.get(url, timeout=30)
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"返回数据结构: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
    print(f"\n完整keys: {data.keys()}")
    if 'data' in data:
        print(f"data的keys: {data['data'].keys()}")
        if 'articles' in data['data']:
            print(f"articles数量: {len(data['data']['articles'])}")
            if data['data']['articles']:
                print(f"第一篇文章的keys: {data['data']['articles'][0].keys()}")
                print(f"第一篇文章示例: {json.dumps(data['data']['articles'][0], indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"错误: {e}")

print("\n" + "=" * 80)
print("2. 测试SOTA开源项目API")
print("=" * 80)
try:
    url = "https://sota.jiqizhixin.com/api/v2/sota/terms?order=generationAt&per=8&page=1"
    response = requests.get(url, timeout=30)
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"返回数据结构: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
    print(f"\n完整keys: {data.keys()}")
    if 'data' in data:
        print(f"data类型: {type(data['data'])}")
        if isinstance(data['data'], list) and data['data']:
            print(f"data数量: {len(data['data'])}")
            print(f"第一个项目的keys: {data['data'][0].keys()}")
            print(f"第一个项目示例: {json.dumps(data['data'][0], indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"错误: {e}")

print("\n" + "=" * 80)
print("3. 测试站长之家实时新闻API (type=1) - 添加headers")
print("=" * 80)
try:
    url = "https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx?flag=zh_cn&type=1&page=1&pagesize=20"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://app.chinaz.com/',
        'Accept': 'application/json, text/plain, */*',
    }
    response = requests.get(url, headers=headers, timeout=30)
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"返回数据结构: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
    print(f"\n完整keys: {data.keys()}")
    if 'data' in data:
        print(f"data类型: {type(data['data'])}")
        if isinstance(data['data'], list) and data['data']:
            print(f"data数量: {len(data['data'])}")
            print(f"第一条新闻的keys: {data['data'][0].keys()}")
            print(f"第一条新闻示例: {json.dumps(data['data'][0], indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"错误: {e}")

print("\n" + "=" * 80)
print("4. 测试站长之家AI产品API (type=2) - 添加headers")
print("=" * 80)
try:
    url = "https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx?flag=zh_cn&type=2&page=1&pagesize=20"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://app.chinaz.com/',
        'Accept': 'application/json, text/plain, */*',
    }
    response = requests.get(url, headers=headers, timeout=30)
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"返回数据结构: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
    print(f"\n完整keys: {data.keys()}")
    if 'data' in data:
        print(f"data类型: {type(data['data'])}")
        if isinstance(data['data'], list) and data['data']:
            print(f"data数量: {len(data['data'])}")
except Exception as e:
    print(f"错误: {e}")
