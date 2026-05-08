#!/usr/bin/env python3
# coding: utf-8
import socket, time, timeit, re, os, sys, json, subprocess, threading
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

# ======= 基础配置 (由命令行参数覆盖) =======
SERVER, USER, PORT, PASSWORD = "127.0.0.1", "chr_v4", 35601, "USER_DEFAULT_PASSWORD"
INTERVAL, PROBEPORT, PING_HISTORY = 3, 53, 100

# 探测点定义
V4_NODES = ["119.29.29.29", "223.5.5.5", "114.114.114.114"]
V6_NODES = ["2402:4e00::", "2400:3200::1", "240c::6666"]

# 参数解析
for argc in sys.argv:
    if 'SERVER=' in argc: SERVER = argc.split('SERVER=')[-1]
    if 'USER=' in argc: USER = argc.split('USER=')[-1]
    if 'PASSWORD=' in argc: PASSWORD = argc.split('PASSWORD=')[-1]

# 自动识别模式
if "_v6" in USER:
    CU, CT, CM = V6_NODES
    print("Mode: IPv6 Monitoring")
else:
    CU, CT, CM = V4_NODES
    print("Mode: IPv4 Monitoring")

# ======= 采集逻辑 (保持原样) =======
def get_uptime():
    with open('/proc/uptime', 'r') as f: return int(f.readline().split('.')[0])

def get_memory():
    re_parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)')
    res = {}
    for line in open('/proc/meminfo'):
        match = re_parser.match(line)
        if match: res[match.group('key')] = int(match.group('value'))
    MemTotal = res['MemTotal']
    MemUsed = MemTotal - res['MemFree'] - res['Buffers'] - res['Cached'] - res.get('SReclaimable', 0)
    return int(MemTotal), int(MemUsed), res['SwapTotal'], res['SwapFree']

def get_hdd():
    try:
        p = subprocess.check_output(['df', '-Tlm', '--total', '-t', 'ext4', '-t', 'xfs']).decode("Utf-8")
        total = p.splitlines()[-1].split()
        return int(total[2]), int(total[3])
    except: return 0, 0

def get_cpu():
    def stat():
        with open("/proc/stat") as f: return [int(x) for x in f.readline().split()[1:5]]
    t1 = stat()
    time.sleep(INTERVAL)
    t2 = stat()
    diff = [t2[i]-t1[i] for i in range(4)]
    st = sum(diff)
    return round(100-(diff[3]*100.0/(st if st else 1)), 1)

def liuliang():
    ni, no = 0, 0
    with open('/proc/net/dev') as f:
        for line in f.readlines():
            if ':' not in line or any(x in line for x in ['lo', 'tun', 'docker', 'veth', 'br-']): continue
            it = line.split(':')[1].split()
            ni += int(it[0]); no += int(it[8])
    return ni, no

# ======= 网络探测 (保持原样) =======
lostRate = {'10010':0.0, '189':0.0, '10086':0.0}
pingTime = {'10010':0, '189':0, '10086':0}
netSpeed = {'rx':0, 'tx':0, 'clock':time.time(), 'avgrx':0, 'avgtx':0}

def _ping_thread(host, mark):
    q = Queue(maxsize=PING_HISTORY)
    lost = 0
    while True:
        if q.full() and q.get() == 0: lost -= 1
        try:
            b = timeit.default_timer()
            fam = socket.AF_INET6 if ":" in host else socket.AF_INET
            s = socket.socket(fam, socket.SOCK_STREAM)
            s.settimeout(1); s.connect((host, PROBEPORT)); s.close()
            pingTime[mark] = int((timeit.default_timer()-b)*1000)
            q.put(1)
        except:
            lost += 1; q.put(0)
        if q.qsize() > 10: lostRate[mark] = float(lost)/q.qsize()
        time.sleep(INTERVAL)

def _net_speed():
    while True:
        rx, tx = liuliang()
        now = time.time()
        diff = now - netSpeed['clock']
        if diff > 0:
            netSpeed['rx'] = int((rx - netSpeed['avgrx'])/diff)
            netSpeed['tx'] = int((tx - netSpeed['avgtx'])/diff)
        netSpeed.update({'clock':now, 'avgrx':rx, 'avgtx':tx})
        time.sleep(INTERVAL)

if __name__ == '__main__':
    for h, m in [(CU,'10010'), (CT,'189'), (CM,'10086')]:
        threading.Thread(target=_ping_thread, args=(h,m), daemon=True).start()
    threading.Thread(target=_net_speed, daemon=True).start()
    
    while True:
        try:
            s = socket.create_connection((SERVER, PORT))
            data = s.recv(1024).decode()
            if "Authentication required" in data:
                s.send(f"{USER}:{PASSWORD}\n".encode())
                data = s.recv(1024).decode()
                if "Authentication successful" not in data: raise Exception("Auth Failed")
            
            check_ip = 6 if "IPv4" in data else 4
            while True:
                mt, mu, st, sf = get_memory()
                ht, hu = get_hdd()
                ni, no = liuliang()
                arr = {
                    'uptime': get_uptime(), 'load_1': os.getloadavg()[0],
                    'memory_total': mt, 'memory_used': mu, 'swap_total': st, 'swap_used': st-sf,
                    'hdd_total': ht, 'hdd_used': hu, 'cpu': get_cpu(),
                    'network_rx': netSpeed['rx'], 'network_tx': netSpeed['tx'],
                    'network_in': ni, 'network_out': no,
                    'ping_10010': lostRate['10010']*100, 'ping_189': lostRate['189']*100, 'ping_10086': lostRate['10086']*100,
                    'time_10010': pingTime['10010'], 'time_189': pingTime['189'], 'time_10086': pingTime['10086'],
                    'tcp':0, 'udp':0, 'process':0, 'thread':0, 'online'+str(check_ip): True
                }
                s.send(f"update {json.dumps(arr)}\n".encode())
        except: time.sleep(3)
