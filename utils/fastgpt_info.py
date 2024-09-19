from pymongo import MongoClient
from datetime import datetime
# 连接到MongoDB
username = 'root'
password = '521666'
connect_string = "mongodb://192.168.16.13"
client = MongoClient(connect_string,
                     username=username,
                     password=password,
                     connect=True,
                     serverSelectionTimeoutMS=3000)
db = client.fastgpt
collection = db.chatitems
# 创建查询条件
query = {"time": {"$gt": datetime(2024, 8, 1)}}
document_count = collection.count_documents(query)
print(document_count)