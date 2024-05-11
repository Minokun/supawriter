# -*- coding: utf-8 -*-
# 写一个天气查询的fastapi应用
import uvicorn
from fastapi import FastAPI
from utils.gd_weather_query import *
import settings

app = FastAPI()

@app.get("/weather")
def weather(city: str):
    weather_json = query_weather(city)
    return weather_json

@app.get("/")
# 返回一个简单的Hello World页面
def index():
    return "<h1>Hello World!</h1>"

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=settings.SERVER_PORT)
