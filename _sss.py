#!/usr/bin/env python3
# coding: utf-8
# Modified for Dual-Stack Support (IPv4 + IPv6)

import json
import sys
import os
import requests
import random, string
import subprocess
import uuid

CONFIG_FILE = "config.json"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/jscntw/serverstatus/master"
IP_URL = "https://api.ipify.org"
jjs = {}
ip = ""

def how2agent(user, passwd):
    print("\n" + "="*50)
    print(f"推荐：使用全能脚本安装双栈监控 (IPv4 + IPv6)")
    print("-" * 50)
    # 修改此处：指向全新的 sss.sh 脚本
    print('wget -N --no-check-certificate {0}/sss.sh && chmod +x sss.sh && sudo ./sss.sh {1} {2} {3}'.format(GITHUB_RAW_URL, getIP(), user, passwd))
    print("="*50 + "\n")
    print(f"注意：服务端 config.json 已自动为该用户预留 _v4 和 _v6 后缀。")

def getIP():
    global ip
    if ip == "":
        try:
            ip = requests.get(IP_URL, timeout=10).content.decode('utf8')
        except:
            ip = "你的服务端IP"
    return ip

def restartSSS():
    # 尝试使用 docker-compose 重启服务端以加载新配置
    print("> 正在尝试重启服务端容器...")
    try:
        subprocess.run(["docker-compose", "restart"], check=True)
    except Exception as e:
        print(f"> 重启失败，请手动执行 docker-compose restart。错误: {e}")

def getPasswd():
    sz = '123456789'
    all_chars = sz + 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    mima = [random.choice(sz), random.choice('abcdefg'), random.choice('ABCDEFG')]
    mima.extend(random.sample(all_chars, 9))
    random.shuffle(mima)
    return "".join(mima)

def saveJJs():
    jjs['servers'] = sorted(jjs['servers'], key=lambda d: d['name']) 
    with open(CONFIG_FILE, "w") as f:
        f.write(json.dumps(jjs, indent=4))

def _show():
    print("\n--- 当前节点列表 ---")
    if not jjs.get('servers'):
        print('>>> 暂无任何节点，请选择添加！ <<<')
        return
    
    for idx, item in enumerate(jjs['servers']):
        print(f"{idx}. 名字: {item['name']} | 用户名: {item['username']} | 位置: {item['location']}")
    print("-" * 20)

def show():
    _show()
    _back()

def _back():
    print("\n>>> 按回车键返回上级菜单")
    input()
    cmd()

def add():
    print('>>> 请输入节点名字 (例如: HK-01):')
    jjname = input().strip()
    if jjname == "":
        print("输入不能为空")
        _back()
        return

    print(f'>>> 请输入 {jjname} 的位置 (默认: us):')
    jjloc = input().strip() or "us"
    
    print(f'>>> 请输入 {jjname} 的虚拟化类型 (默认: kvm):')
    jjtype = input().strip() or "kvm"

    # 生成基础配置
    # 注意：我们的 Agent 脚本会自动在用户名后加 _v4 和 _v6
    # 因此我们在这里生成一个基础用户名，由 Agent 去匹配后缀
    common_user = uuid.uuid4().hex[:8] # 取简短的 8 位
    common_pass = getPasswd()

    item = {
        "name": jjname,
        "location": jjloc,
        "type": jjtype,
        "host": jjname,
        "monthstart": 1,
        "username": common_user,
        "password": common_pass
    }

    jjs['servers'].append(item)
    saveJJs()
    
    print(f"\n{green}节点添加成功！正在重启服务...{plain}")
    restartSSS()
    
    _show()
    how2agent(common_user, common_pass)
    _back()

def update():
    _show()
    print(">>> 请输入需要更新的节点编号：")
    idx = input()
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
    print("更新成功!")
    _back()

def remove():
    _show()
    print(">>> 请输入需要删除的节点编号：")
    idx = input()
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
    print("删除成功!")
    _back()

def cmd():
    print("\n" + "="*40)
    print("  Server Status 节点管理工具 (双栈适配版)")
    print("="*40)
    print('1. 查看节点')
    print('2. 添加节点')
    print('3. 删除节点')
    print('4. 更新节点')
    print('0. 退出')
    
    choice = input("\n请输入操作编号: ").strip()
    if choice == '1': show()
    elif choice == '2': add()
    elif choice == '3': remove()
    elif choice == '4': update()
    elif choice == '0': sys.exit()
    else:
        print("无效输入")
        cmd()

if __name__ == '__main__':
    # 颜色代码适配简单的终端输出
    green, plain = '\033[0;32m', '\033[0m'
    
    if not os.path.exists(CONFIG_FILE):
        print(f"错误: 找不到 {CONFIG_FILE}，请确保在服务端目录下运行。")
        # 尝试创建一个空配置
        with open(CONFIG_FILE, "w") as f:
            f.write('{"servers":[]}')
    
    with open(CONFIG_FILE, "r") as f:
        try:
            jjs = json.load(f)
        except:
            jjs = {"servers": []}
    
    cmd()
