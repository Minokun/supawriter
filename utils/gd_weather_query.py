# coding=utf-8
import requests
import json
import pandas as pd

# 从Amap_adcode_citycode.json中读取json数据
with open('utils/AMap_adcode_citycode.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
# 将json转为pandas
pd_data = pd.DataFrame(data)

def query_weather(city: str):
    # 读取城市编码
    select_city = pd_data[pd_data["city"].str.contains(city)]
    select_list = select_city.adcode.values
    if len(select_list) == 0:
        return "没有找到该城市"
    else:
        abcode = select_list[0]
    # 访问高德天气插叙api，get请求：
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={abcode}&extensions=all&key=189a6d3a49f6bc96c273029eb9aa6af5"
    response = requests.get(url)
    weather_json = response.json()
    return weather_json
