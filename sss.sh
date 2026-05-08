#!/bin/bash
#========================================================
#   System Required: CentOS 7+ / Debian 8+ / Ubuntu 16+
#   Description: Server Status 全能管理脚本 (适配 Dockge)
#   Github: https://github.com/jscntw/serverstatus
#========================================================

# 基础目录与 URL
# 修改点：将 SERVER 路径与 BASE 路径统一，方便 Dockge 识别
SSS_BASE_PATH="/opt/stacks/sss"
SSS_AGENT_PATH="${SSS_BASE_PATH}/agent"
SSS_SERVER_PATH="${SSS_BASE_PATH}"
GITHUB_RAW_URL="https://raw.githubusercontent.com/jscntw/serverstatus/master"

# 颜色定义
red='\033[0;31m'
green='\033[0;32m'
yellow='\033[0;33m'
plain='\033[0m'

export PATH=$PATH:/usr/local/bin

# 1. 基础检查
pre_check() {
    command -v systemctl >/dev/null 2>&1
    if [[ $? != 0 ]]; then
        echo "不支持此系统：未找到 systemctl 命令"
        exit 1
    fi
    [[ $EUID -ne 0 ]] && echo -e "${red}错误: ${plain} 必须使用root用户运行此脚本！\n" && exit 1
}

# 2. 软件安装工具
install_soft() {
    (command -v yum >/dev/null 2>&1 && yum install $* -y) ||
        (command -v apt >/dev/null 2>&1 && apt update && apt install $* -y) ||
        (command -v pacman >/dev/null 2>&1 && pacman -Syu $*) ||
        (command -v apt-get >/dev/null 2>&1 && apt update && apt-get install $* -y)
}

install_base() {
    echo -e "> 安装基础依赖..."
    (command -v curl >/dev/null 2>&1 && command -v wget >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1) || \
        install_soft curl wget python3 python3-pip
    pip3 install requests --quiet >/dev/null 2>&1
}

# 3. Docker 环境安装
install_docker() {
    command -v docker >/dev/null 2>&1
    if [[ $? != 0 ]]; then
        echo -e "> 正在安装 Docker..."
        bash <(curl -sL https://get.docker.com) >/dev/null 2>&1
        systemctl enable docker.service && systemctl start docker.service
    fi
    # 优先使用 docker compose (V2)
    if ! docker compose version >/dev/null 2>&1; then
        echo -e "> 正在安装 Docker Compose V2..."
        install_soft docker-compose-plugin
    fi
}

# ==================== 服务端 (Master) 逻辑 ====================
install_dashboard() {
    install_base
    install_docker
    mkdir -p $SSS_SERVER_PATH && cd $SSS_SERVER_PATH
    
    echo -e "> 下载服务端组件到 ${SSS_SERVER_PATH}..."
    wget -qO compose.yaml ${GITHUB_RAW_URL}/compose.yaml
    wget -qO Dockerfile ${GITHUB_RAW_URL}/Dockerfile
    wget -qO bot.py ${GITHUB_RAW_URL}/bot.py
    wget -qO _sss.py ${GITHUB_RAW_URL}/_sss.py
    
    if [ ! -f config.json ]; then
        echo '{"servers":[]}' > config.json
    fi

    # TG Bot 配置
    if [[ $# == 2 ]]; then
        sed -i "s/tg_chat_id/$1/" compose.yaml
        sed -i "s/tg_bot_token/$2/" compose.yaml
        echo -e "> 已自动配置 Telegram Bot 信息"
    fi

    echo -e "> 启动 Docker 容器..."
    docker compose up -d
    
    echo -e "${green}服务端安装完成！${plain}"
    echo -e "${yellow}Dockge 提示：你可以在 Dockge 面板中看到名为 'sss' 的栈了。${plain}"
    
    # 进入管理模式
    python3 _sss.py
}

# ==================== 受控端 (Agent) 逻辑 ====================
install_agent() {
    install_base
    mkdir -p $SSS_AGENT_PATH && chmod 777 -R $SSS_AGENT_PATH
    
    echo -e "> 下载受控端脚本 (IPv4 + IPv6)..."
    wget -qO $SSS_AGENT_PATH/client-linux.py ${GITHUB_RAW_URL}/client-linux.py
    wget -qO $SSS_AGENT_PATH/client-linux-v6.py ${GITHUB_RAW_URL}/client-linux-v6.py

    if [ $# -lt 3 ]; then
        echo -e "${yellow}请设置 Agent 配置参数：${plain}"
        read -p "服务端域名/IP: " s_host
        read -p "用户名: " s_user
        read -p "密码: " s_pass
    else
        s_host=$1; s_user=$2; s_pass=$3
    fi

    for proto in "v4" "v6"; do
        svc_name="sss-agent"
        target_user="${s_user}_v4"
        if [ "$proto" == "v6" ]; then
            svc_name="sss-agent-v6"
            target_user="${s_user}_v6"
        fi
        
        wget -qO /etc/systemd/system/${svc_name}.service ${GITHUB_RAW_URL}/${svc_name}.service
        sed -i "s/sss_host/${s_host}/" /etc/systemd/system/${svc_name}.service
        sed -i "s/sss_user/${target_user}/" /etc/systemd/system/${svc_name}.service
        sed -i "s/sss_pass/${s_pass}/" /etc/systemd/system/${svc_name}.service
        
        systemctl daemon-reload
        systemctl enable $svc_name && systemctl restart $svc_name
    done
    echo -e "${green}双栈 Agent 已启动：${plain} ${s_user}_v4 / ${s_user}_v6"
}

# ==================== 卸载与菜单 ====================
uninstall_all() {
    echo -e "${red}> 正在清理所有环境...${plain}"
    systemctl stop sss-agent sss-agent-v6 >/dev/null 2>&1
    systemctl disable sss-agent sss-agent-v6 >/dev/null 2>&1
    rm -f /etc/systemd/system/sss-agent*
    
    if [ -d "$SSS_SERVER_PATH" ]; then
        cd $SSS_SERVER_PATH && docker compose down >/dev/null 2>&1
    fi
    rm -rf $SSS_BASE_PATH
    systemctl daemon-reload
    echo -e "${green}卸载完成！${plain}"
}

show_menu() {
    clear
    echo -e "
    ${green}Server Status 全能管理脚本 (Dockge 适配版)${plain}
    --- https://github.com/jscntw/serverstatus ---
    
    ${yellow}服务端 (Master)：${plain}
    ${green}1.${plain}  安装服务端 (直接部署到 /opt/stacks/sss)
    ${green}2.${plain}  管理节点 (添加/删除/查看)
    
    ${yellow}受控端 (Agent)：${plain}
    ${green}3.${plain}  安装双栈监控 (IPv4 + IPv6)
    
    ${yellow}通用：${plain}
    ${green}4.${plain}  完全卸载
    ${green}0.${plain}  退出
    "
    read -ep "请输入选择 [0-4]: " num
    case "${num}" in
        1) install_dashboard "$@" ;;
        2) [ -d "$SSS_SERVER_PATH" ] && cd $SSS_SERVER_PATH && python3 _sss.py || echo "未发现服务端" ;;
        3) install_agent "$@" ;;
        4) uninstall_all ;;
        *) exit 0 ;;
    esac
}

# 脚本入口
pre_check
if [[ $# == 3 ]]; then
    install_agent "$@"
elif [[ $# == 2 ]]; then
    # 如果带了两个参数（ID 和 Token），直接跑安装逻辑
    install_dashboard "$@"
else
    show_menu
fi
