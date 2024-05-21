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
    
    Chipset
    Chipset：Q170
    
    BIOS
    BIOS：AMI UEFI BIOS (Support Watchdog Timer)
    
    Memory
    Socket：2 * Non-ECC SO-DIMM Slot, Dual Channel DDR4 up to 2133MHz
    Max Capacity：64GB, Single Max. 32GB
    
    Graphics
    Controller：Intel® HD Graphics
    
    Ethernet
    Controller：	1 * Intel i210-AT GbE LAN Chip (10/100/1000 Mbps)、1 * Intel i219-LM/V GbE LAN Chip (10/100/1000 Mbps)
    
    Storage
    SATA：1 * SATA3.0, quick release 2.5-inch hard drive bay (T ≤ 7mm)、1 * SATA3.0, Internal 2.5" hard disk bays (T≤9mm, Optional)、Support RAID 0, 1
    M.2：	1 * M.2 Key-M (PCIe x4 Gen 3 + SATA3.0、NVMe/SATA SSD Auto Detect, 2242/2260/2280)
    
    Expansin Slots
    PCIe/PCI：	N/A
    MXM/aDoor：	1 * APQ MXM /aDoor Bus (Optional MXM 4 * LAN/4 * POE/6 * COM/16 * GPIO expansion card)1 * aDoor Expansion Slot
    Mini PCIe：1 * Mini PCIe (PCIe x1 Gen 2 + USB 2.0, with 1 * SIM Card)
    M.2：	1 * M.2 Key-B (PCIe x1 Gen 2 + USB3.0, with 1 * SIM Card, 3042/3052)
    
    Front I/O
    Ethernet：	2 * RJ45
    USB：	6 * USB3.0 (Type-A, 5Gbps)
    Display：	1 * DVI-D: max resolution up to 1920*1200 @ 60Hz、1 * VGA (DB15/F): max resolution up to 1920*1200 @ 60Hz、1 * DP: max resolution up to 4096*2160 @ 60Hz
    Audio：	2 * 3.5mm Jack (Line-Out + MIC)
    Serial：	2 * RS232/422/485 (COM1/2, DB9/M, Full Lanes, BIOS Switch)、2 * RS232 (COM3/4, DB9/M)
    Button：	1 * Power Button + Power LED、1 * System Reset Button (Hold down 0.2 to 1s to restart, and hold down 3s to clear CMOS)
    
    Rear I/O
    Antenna：	4 * Antenna hole
    SIM	：	2 * Nano SIM card slots
    
    Internal I/O
    USB	：2 * USB2.0 (wafer)
    LCD：	1 * LVDS (wafer): max resolution up to 1920*1200 @ 60Hz
    TFront Panel	：1 * TF_Panel (3 * USB 2.0 + FPANEL, wafer)
    Front Panel：	1 * FPanel (PWR + RST + LED, wafer)
    Speaker：	1 * Speaker (2-W (per channel)/8-Ω Loads, wafer)
    Serial：	2 * RS232 (COM5/6, wafer)
    GPIO：	1 * 16 bits DIO (8xDI and 8xDO, wafer)
    LPC：	1 * LPC (wafer)
    SATA：	2 * SATA 7P Connector
    SATA Power：	2 * SATA Power (wafer)
    FAN	：1 * CPU FAN (wafer)、2 * SYS FAN (wafer)
    
    Power Supply
    Type：	DC, AT/ATX
    Power Input Voltage：	9 ~ 36VDC, P≤240W
    Connector：	1 * 4Pin Connector, P=5.00/5.08
    RTC Battery：	CR2032 Coin Cell
    
    OS Support
    Windows：	6/7th Core™: Windows 7/10/11、8/9th Core™: Windows 10/11
    Linux：	Linux
    
    Watchdog
    Output：	System Reset
    Interval：	Programmable via Software from 1 to 255 sec
    
    Mechanical
    Enclosure Material：	Radiator: Aluminum alloy, Box: SGCC
    Dimensions：	268mm(L) * 194.2mm(W) * 67.7mm(H)	
    Weight：	Net: 4.5 kgTotal: 6 kg (Include packaging)	
    Mounting：	VESA, Wall mounted, Desktop
    
    Environment
    Heat Dissipation System：	Fanless Passive Cooling
    Operating Temperature：	-20~60℃ (Industrial SSD)
    Storage Temperature：	-40~80℃ (Industrial SSD)
    Relative Humidity：	10 to 90% RH (non-condensing)
    Vibration During Operation：	With SSD: IEC 60068-2-64 (3Grms@5~500Hz, random, 1hr/axis)
    Shock During Operation：	With SSD: IEC 60068-2-27 (30G, half sine, 11ms)
    Certification：	CCC, CE/FCC, RoHS
    '''})

@app.get("/")
# 返回一个简单的Hello World页面
def index():
    return "<h1>Hello World!</h1>"

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=settings.SERVER_PORT)
