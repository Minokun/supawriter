# -*- coding: utf-8 -*-
# 写一个天气查询的fastapi应用
import json

import uvicorn
from fastapi import FastAPI
from utils.gd_weather_query import *
from utils.searxng_utils import Search
import settings
import asyncio

search_obj = Search(result_num=5)
app = FastAPI()

@app.get("/weather")
def weather(city: str):
    weather_json = query_weather(city)
    return weather_json

@app.get("/search")
def search(question: str):
    global search_obj
    result = search_obj.run(question, return_type='search')
    return result

@app.get("/search_spider")
def search(question: str):
    global search_obj
    result = search_obj.run(question, return_type='search_spider')
    return result

@app.get("/pdu_spec")
def pdu_spec(pdu: str):
    return json.dumps({f"{pdu}_spec": '''
    CPU：Intel® 6/7/8/9th Generation Core / Pentium/ Celeron Desktop CPU
    TDP：35W
    Socket：LGA1151
    
    '''})

@app.get("/")
# 返回一个简单的Hello World页面
def index():
    return "<h1>Hello World!</h1>"

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=settings.WEB_SERVER_PORT)
