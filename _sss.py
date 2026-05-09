#!/usr/bin/env python3
# coding: utf-8
# Optimized for Dual-Stack Support (IPv4 + IPv6) - Auto-split V4/V6 Slots

import json
import sys
import os
import requests
import random
import string
import subprocess
import uuid

CONFIG_FILE = "config.json"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/jscntw/chr-serverstatus/master"
IP_URL = "https://api.ipify.org"

jjs = {}
ip = ""

# 颜色定义
green = '\033[0;32m'
yellow = '\033[0;33m'
plain = '\033[0m'

def how2agent(user, passwd):
    print("\n" + "="*60)
    print(f"{green}推荐：使用全能脚本一键安装双栈监控 (IPv4 + IPv6){plain}")
    print("-" * 60)
    # 传递基础 user，sss.sh 内部会自动加后缀安装两个 service
    print(f'wget -N --no-check-certificate {GITHUB_RAW_URL}/sss.sh && chmod +x sss.sh && sudo ./sss.sh {getIP()} {user} {passwd}')
    print("="*60 + "\n")
    print(f"{yellow}提示：服务端已自动为您在 config.json 中创建了 {user}_v4 和 {user}_v6 两个槽位。{plain}")

def getIP():
    global ip
    if ip == "":
        try:
            ip = requests.get(IP_URL, timeout=10).content.decode('utf8')
        except:
            ip = "你的服务端IP"
    return ip

def restartSSS():
    print("> 正在尝试重启服务端容器以加载新配置...")
    # 优先尝试 docker compose，兼容旧版 docker-compose
    for cmd_base in [["docker", "compose"], ["docker-compose"]]:
        try:
            subprocess.run(cmd_base + ["restart"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"> {green}服务重启成功！{plain}")
            return
        except:
            continue
    print(f"> {yellow}重启失败，请稍后手动执行 docker compose restart。{plain}")

def getPasswd():
    sz = '123456789'
    all_chars = sz + 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    mima = [random.choice(sz), random.choice('abcdefg'), random.choice('ABCDEFG')]
    mima.extend(random.sample(all_chars, 9))
    random.shuffle(mima)
    return "".join(mima)

def saveJJs():
    # 按名字排序，让面板显示更有序
    if 'servers' in jjs:
        jjs['servers'] = sorted(jjs['servers'], key=lambda d: d.get('name', '')) 
    with open(CONFIG_FILE, "w", encoding='utf-8') as f:
        f.write(json.dumps(jjs, indent=4, ensure_ascii=False))

def _show():
    print("\n--- 当前节点列表 ---")
    if not jjs.get('servers'):
        print('>>> 暂无任何节点，请选择添加！ <<<')
        return
    
    for idx, item in enumerate(jjs['servers']):
        print(f"[{idx}] 名字: {item.get('name')} | 用户名: {item.get('username')} | 位置: {item.get('location')}")
    print("-" * 30)

def show():
    _show()
    _back()

def _back():
    print("\n>>> 按回车键返回主菜单")
    input()
    cmd()

def add():
    print('>>> 请输入节点显示名字 (例如: Aliyun-HK):')
    jjname = input().strip()
    if not jjname:
        print("输入不能为空")
        _back()
        return
        
    print(f'>>> 请输入 {jjname} 的位置 (默认: cn):')
    jjloc = input().strip() or "cn"
        
    print(f'>>> 请输入 {jjname} 的虚拟化类型 (默认: kvm):')
    jjtype = input().strip() or "kvm"

    # 1. 生成一套基础账号
    common_user = uuid.uuid4().hex[:8] 
    common_pass = getPasswd()

    # 2. 核心修改：循环创建两个节点（v4 和 v6）
    # 这样受控端运行一次脚本，服务端两个坑位都能对齐数据
    for suffix in ["v4", "v6"]:
        item = {
            "name": f"{jjname}_{suffix.upper()}",
            "location": jjloc,
            "type": jjtype,
            "host": jjname,
            "monthstart": 1,
            "username": f"{common_user}_{suffix}", # 生成 user_v4 和 user_v6
            "password": common_pass
        }
        jjs['servers'].append(item)
    
    saveJJs()
    print(f"\n{green}双栈节点配置已写入！{plain}")
    restartSSS()
    
    # 引导用户安装
    how2agent(common_user, common_pass)
    _back()

def update():
    _show()
    print(">>> 请输入需要更新的节点编号：")
    idx = input().strip()
    if not idx.isnumeric() or int(idx) >= len(jjs['servers']):
        print('无效输入')
        _back()
        return
        
    jj = jjs['servers'][int(idx)]
    print(f'>>> 修改节点: {jj["name"]}')
        
    new_name = input(f"新名字 [{jj['name']}]: ").strip() or jj['name']
    new_loc = input(f"新位置 [{jj['location']}]: ").strip() or jj['location']
    new_type = input(f"新类型 [{jj['type']}]: ").strip() or jj['type']
        
    jjs['servers'][int(idx)].update({
        "name": new_name,
        "location": new_loc,
        "type": new_type
    })
        
    saveJJs()
    restartSSS()
    print(f"{green}更新成功!{plain}")
    _back()

def remove():
    _show()
    print(">>> 请输入需要删除的节点编号：")
    idx = input().strip()
    if not idx.isnumeric() or int(idx) >= len(jjs['servers']):
        print('无效输入')
        _back()
        return
        
    target = jjs['servers'][int(idx)]
    confirm = input(f">>> 确定要删除节点 {target['name']} 吗？[Y/n]: ")
    if confirm.lower() == 'n':
        _back()
        return
        
    del jjs['servers'][int(idx)]
    saveJJs()
    restartSSS()
    print(f"{green}删除成功!{plain}")
    _back()

def cmd():
    # 清屏
    os.system('clear')
    print("\n" + "="*45)
    print("   Server Status 节点管理工具 (双栈适配版)")
    print("="*45)
    print(' 1. 查看所有节点')
    print(' 2. 添加双栈节点 (一开二)')
    print(' 3. 删除指定节点')
    print(' 4. 修改节点信息')
    print(' 0. 退出')
    print("="*45)
        
    choice = input("\n请输入操作编号: ").strip()
    if choice == '1': show()
    elif choice == '2': add()
    elif choice == '3': remove()
    elif choice == '4': update()
    elif choice == '0': sys.exit()
    else:
        print("无效输入，请重新选择")
        cmd()

if __name__ == '__main__':
    # 初始化检查
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            f.write('{"servers":[]}')
            
    with open(CONFIG_FILE, "r", encoding='utf-8') as f:
        try:
            jjs = json.load(f)
        except:
            jjs = {"servers": []}
            
    cmd()
