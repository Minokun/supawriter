# -*- coding: utf-8 -*-
# 将当前目录目录设置到环境变量中
import os
import sys

base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_path)

SERVER_PORT = 89