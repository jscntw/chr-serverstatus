#!/usr/bin/env python3
# coding: utf-8
# Optimized for Dual-Stack Monitoring

import socket
import time
import timeit
import re
import os
import sys
import json
import errno
import subprocess
import threading

try:
    from queue import Queue     # python3
except ImportError:
    from Queue import Queue     # python2

# ======= 基础配置区 (会被命令行参数覆盖) =======
SERVER = "127.0.0.1"
USER = "chr_v4"
PORT = 35601
PASSWORD = "USER_DEFAULT_PASSWORD"
INTERVAL = 3         # 建议设置为3，降低受控机压力
PROBEPORT = 80
PROBE_PROTOCOL_PREFER = "ipv4"  # 默认为ipv4
PING_PACKET_HISTORY_LEN = 100

# ======= 运营商骨干网探测点 =======
# IPv4 节点
CU_V4 = "219.158.3.145"
CT_V4 = "202.97.12.1"
CM_V4 = "221.183.55.22"

# IPv6 节点
CU_V6 = "2408:8000:1:2::1"
CT_V6 = "240e:97c:2f:1::1"
CM_V6 = "2409:8080:0:1::1"

# 根据协议偏好自动选择探测目标
CU, CT, CM = CU_V4, CT_V4, CM_V4 # 默认初始值

def update_probe_targets():
    global CU, CT, CM
    if PROBE_PROTOCOL_PREFER == "ipv6":
        CU, CT, CM = CU_V6, CT_V6, CM_V6
        print("Monitoring Mode: IPv6 (Backbone Nodes)")
    else:
        CU, CT, CM = CU_V4, CT_V4, CM_V4
        print("Monitoring Mode: IPv4 (Backbone Nodes)")

# ======= 系统信息采集函数 =======

def get_uptime():
    with open('/proc/uptime', 'r') as f:
        uptime = f.readline().split('.', 2)
        return int(uptime[0])

def get_memory():
    re_parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB')
    result = dict()
    for line in open('/proc/meminfo'):
        match = re_parser.match(line)
        if not match:
            continue
        key, value = match.groups(['key', 'value'])
        result[key] = int(value)
    MemTotal = float(result['MemTotal'])
    MemUsed = MemTotal-float(result['MemFree'])-float(result['Buffers'])-float(result['Cached'])-float(result['SReclaimable'])
    SwapTotal = float(result['SwapTotal'])
    SwapFree = float(result['SwapFree'])
    return int(MemTotal), int(MemUsed), int(SwapTotal), int(SwapFree)

def get_hdd():
    try:
        p = subprocess.check_output(['df', '-Tlm', '--total', '-t', 'ext4', '-t', 'ext3', '-t', 'ext2', '-t', 'reiserfs', '-t', 'jfs', '-t', 'ntfs', '-t', 'fat32', '-t', 'btrfs', '-t', 'fuseblk', '-t', 'zfs', '-t', 'simfs', '-t', 'xfs']).decode("Utf-8")
        total = p.splitlines()[-1]
        used = total.split()[3]
        size = total.split()[2]
        return int(size), int(used)
    except:
        return 0, 0

def get_time():
    with open("/proc/stat", "r") as f:
        time_list = f.readline().split(' ')[2:6]
        for i in range(len(time_list)):
            time_list[i] = int(time_list[i])
        return time_list

def delta_time():
    x = get_time()
    time.sleep(INTERVAL)
    y = get_time()
    for i in range(len(x)):
        y[i]-=x[i]
    return y

def get_cpu():
    t = delta_time()
    st = sum(t)
    if st == 0:
        st = 1
    result = 100-(t[len(t)-1]*100.00/st)
    return round(result, 1)

def liuliang():
    NET_IN = 0
    NET_OUT = 0
    with open('/proc/net/dev') as f:
        for line in f.readlines():
            netinfo = re.findall('([^\s]+):[\s]{0,}(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', line)
            if netinfo:
                if netinfo[0][0] == 'lo' or 'tun' in netinfo[0][0] \
                        or 'docker' in netinfo[0][0] or 'veth' in netinfo[0][0] \
                        or 'br-' in netinfo[0][0] or 'vmbr' in netinfo[0][0] \
                        or 'vnet' in netinfo[0][0] or 'kube' in netinfo[0][0] \
                        or netinfo[0][1]=='0' or netinfo[0][9]=='0':
                    continue
                else:
                    NET_IN += int(netinfo[0][1])
                    NET_OUT += int(netinfo[0][9])
    return NET_IN, NET_OUT

def tupd():
    return 0,0,0,0

def get_network(ip_version):
    if(ip_version == 4):
        HOST = "1.1.1.1"
    elif(ip_version == 6):
        HOST = "240c::6666"
    try:
        socket.create_connection((HOST, 53), 2).close()
        return True
    except:
        return False

# ======= 网络探测线程 =======

lostRate = {'10010': 0.0, '189': 0.0, '10086': 0.0}
pingTime = {'10010': 0, '189': 0, '10086': 0}
netSpeed = {'netrx': 0.0, 'nettx': 0.0, 'clock': 0.0, 'diff': 0.0, 'avgrx': 0, 'avgtx': 0}

def _ping_thread(host, mark, port):
    lostPacket = 0
    packet_queue = Queue(maxsize=PING_PACKET_HISTORY_LEN)
    while True:
        if packet_queue.full():
            if packet_queue.get() == 0:
                lostPacket -= 1
        try:
            b = timeit.default_timer()
            # 兼容 IPv4/IPv6 的连接测试
            family = socket.AF_INET6 if ":" in host else socket.AF_INET
            s = socket.socket(family, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((host, port))
            s.close()
            pingTime[mark] = int((timeit.default_timer() - b) * 1000)
            packet_queue.put(1)
        except:
            lostPacket += 1
            packet_queue.put(0)
        
        if packet_queue.qsize() > 30:
            lostRate[mark] = float(lostPacket) / packet_queue.qsize()
        time.sleep(INTERVAL)

def _net_speed():
    while True:
        with open("/proc/net/dev", "r") as f:
            net_dev = f.readlines()
            avgrx = 0
            avgtx = 0
            for dev in net_dev[2:]:
                dev = dev.split(':')
                if "lo" in dev[0] or "tun" in dev[0] \
                        or "docker" in dev[0] or "veth" in dev[0] \
                        or "br-" in dev[0] or "vmbr" in dev[0] \
                        or "vnet" in dev[0] or "kube" in dev[0]:
                    continue
                dev = dev[1].split()
                avgrx += int(dev[0])
                avgtx += int(dev[8])
            now_clock = time.time()
            netSpeed["diff"] = now_clock - netSpeed["clock"]
            netSpeed["clock"] = now_clock
            if netSpeed["diff"] > 0:
                netSpeed["netrx"] = int((avgrx - netSpeed["avgrx"]) / netSpeed["diff"])
                netSpeed["nettx"] = int((avgtx - netSpeed["avgtx"]) / netSpeed["diff"])
            netSpeed["avgrx"] = avgrx
            netSpeed["avgtx"] = avgtx
        time.sleep(INTERVAL)

def get_realtime_date():
    t1 = threading.Thread(target=_ping_thread, kwargs={'host': CU, 'mark': '10010', 'port': PROBEPORT})
    t2 = threading.Thread(target=_ping_thread, kwargs={'host': CT, 'mark': '189', 'port': PROBEPORT})
    t3 = threading.Thread(target=_ping_thread, kwargs={'host': CM, 'mark': '10086', 'port': PROBEPORT})
    t4 = threading.Thread(target=_net_speed)
    for t in [t1, t2, t3, t4]:
        t.setDaemon(True)
        t.start()

def byte_str(object):
    if isinstance(object, str):
        return object.encode(encoding="utf-8")
    elif isinstance(object, bytes):
        return bytes.decode(object)
    return str(object)

if __name__ == '__main__':
    # 处理命令行参数
    for argc in sys.argv:
        if 'SERVER' in argc:
            SERVER = argc.split('SERVER=')[-1]
        elif 'PORT' in argc:
            PORT = int(argc.split('PORT=')[-1])
        elif 'USER' in argc:
            USER = argc.split('USER=')[-1]
        elif 'PASSWORD' in argc:
            PASSWORD = argc.split('PASSWORD=')[-1]
        elif 'INTERVAL' in argc:
            INTERVAL = int(argc.split('INTERVAL=')[-1])
        elif 'PREFER' in argc:
            PROBE_PROTOCOL_PREFER = argc.split('PREFER=')[-1]

    update_probe_targets()
    socket.setdefaulttimeout(30)
    get_realtime_date()

    while True:
        try:
            print("Connecting to Server...")
            s = socket.create_connection((SERVER, PORT))
            data = byte_str(s.recv(1024))
            if "Authentication required" in data:
                s.send(byte_str(USER + ':' + PASSWORD + '\n'))
                data = byte_str(s.recv(1024))
                if "Authentication successful" not in data:
                    raise socket.error
            
            check_ip = 6 if "IPv4" in data else 4
            timer = 0
            
            while True:
                CPU = get_cpu()
                NET_IN, NET_OUT = liuliang()
                MemoryTotal, MemoryUsed, SwapTotal, SwapFree = get_memory()
                HDDTotal, HDDUsed = get_hdd()
                Load_1, _, _ = os.getloadavg()

                array = {
                    'uptime': get_uptime(),
                    'load_1': Load_1,
                    'memory_total': MemoryTotal,
                    'memory_used': MemoryUsed,
                    'swap_total': SwapTotal,
                    'swap_used': SwapTotal - SwapFree,
                    'hdd_total': HDDTotal,
                    'hdd_used': HDDUsed,
                    'cpu': CPU,
                    'network_rx': netSpeed.get("netrx"),
                    'network_tx': netSpeed.get("nettx"),
                    'network_in': NET_IN,
                    'network_out': NET_OUT,
                    'ping_10010': lostRate.get('10010') * 100,
                    'ping_189': lostRate.get('189') * 100,
                    'ping_10086': lostRate.get('10086') * 100,
                    'time_10010': pingTime.get('10010'),
                    'time_189': pingTime.get('189'),
                    'time_10086': pingTime.get('10086'),
                    'tcp': 0, 'udp': 0, 'process': 0, 'thread': 0
                }
                
                if not timer:
                    array['online' + str(check_ip)] = get_network(check_ip)
                    timer = 10
                else:
                    timer -= 1
                
                s.send(byte_str("update " + json.dumps(array) + "\n"))
        except Exception as e:
            print("Error:", e)
            time.sleep(3)
