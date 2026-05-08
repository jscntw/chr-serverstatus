#!/usr/bin/env python3
# coding: utf-8
# 适配双栈监控的 Telegram Bot

import os
import sys
import requests
import time
import traceback

# 这里的 http://sss/ 是 Docker 内部通讯地址，保持不变
NODE_STATUS_URL = 'http://sss/json/stats.json'

offs = []
counterOff = {}
counterOn = {}

def _send(text):
    chat_id = os.getenv('TG_CHAT_ID')
    bot_token = os.environ.get('TG_BOT_TOKEN')
    if not chat_id or not bot_token:
        print("未检测到 TG_CHAT_ID 或 TG_BOT_TOKEN 环境变量")
        return
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
        "chat_id": chat_id,
        "text": text
    }
    try:
        requests.get(url, params=params, timeout=10)
    except Exception as e:
        print("发送失败: ", traceback.format_exc())

def send2tg(srv, flag):
    if srv not in counterOff: counterOff[srv] = 0
    if srv not in counterOn: counterOn[srv] = 0
    
    if flag == 1:  # 节点在线
        if srv in offs:
            # 连续 5 次检测到在线才发送恢复通知（避免网络抖动导致频繁闪报）
            if counterOn[srv] < 5:
                counterOn[srv] += 1
                return
            offs.remove(srv)
            counterOn[srv] = 0
            text = '<b>✅ Server Status 恢复</b>' + '\n节点已上线: ' + srv 
            _send(text)
    else:  # 节点离线
        if srv not in offs:
            # 连续 5 次检测到掉线才报警
            if counterOff[srv] < 5:
                counterOff[srv] += 1
                return
            offs.append(srv)
            counterOff[srv] = 0
            text = '<b>❌ Server Status 报警</b>' + '\n节点已下线: ' + srv 
            _send(text)

def sscmd(address):
    print(f"Bot 已启动，正在监控: {address}")
    while True:
        try:
            r = requests.get(url=address, headers={"User-Agent": "ServerStatus/2026"}, timeout=10)
            jsonR = r.json()
            for i in jsonR["servers"]:
                # 核心逻辑修改：
                # 既然我们已经把 v4 和 v6 拆分成独立的节点（s01_v4, s01_v6）
                # 那么只要该节点的在线状态为 False，就应该报警
                if i["online4"] is False and i["online6"] is False:
                    send2tg(i["name"], 0)
                else:
                    send2tg(i["name"], 1)
        except Exception as e:
            print('连接服务端 JSON 出错，正在重试...')
            time.sleep(10)
            continue
        
        # 每 5 秒检查一次状态
        time.sleep(5)

if __name__ == '__main__':
    sscmd(NODE_STATUS_URL)
