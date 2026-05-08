#!/bin/bash
#========================================================
#   System Required: CentOS 7+ / Debian 8+ / Ubuntu 16+
#   Description: Server Status 监控双栈安装脚本 (IPv4 + IPv6)
#   Github: https://github.com/jscntw/serverstatus
#========================================================

SSS_BASE_PATH="/opt/stacks/sss"
SSS_AGENT_PATH="${SSS_BASE_PATH}/agent"
SSS_AGENT_V4_SERVICE="/etc/systemd/system/sss-agent.service"
SSS_AGENT_V6_SERVICE="/etc/systemd/system/sss-agent-v6.service"
GITHUB_RAW_URL="https://raw.githubusercontent.com/jscntw/serverstatus/master"

red='\033[0;31m'
green='\033[0;32m'
yellow='\033[0;33m'
plain='\033[0m'

export PATH=$PATH:/usr/local/bin

pre_check() {
    command -v systemctl >/dev/null 2>&1
    if [[ $? != 0 ]]; then
        echo "不支持此系统：未找到 systemctl 命令"
        exit 1
    fi
    [[ $EUID -ne 0 ]] && echo -e "${red}错误: ${plain} 必须使用root用户运行此脚本！\n" && exit 1
}

install_soft() {
    (command -v yum >/dev/null 2>&1 && yum install $* -y) ||
        (command -v apt >/dev/null 2>&1 && apt update && apt install $* -y) ||
        (command -v pacman >/dev/null 2>&1 && pacman -Syu $*) ||
        (command -v apt-get >/dev/null 2>&1 && apt update && apt-get install $* -y)
}

install_base() {
    (command -v git >/dev/null 2>&1 && command -v curl >/dev/null 2>&1 && command -v wget >/dev/null 2>&1 && command -v tar >/dev/null 2>&1) ||
        (install_soft curl wget python3)
}

modify_agent_config() {
    echo -e "> 修改Agent配置 (双栈模式)"
    
    # 下载两个服务模板文件
    wget -O $SSS_AGENT_V4_SERVICE ${GITHUB_RAW_URL}/sss-agent.service >/dev/null 2>&1
    wget -O $SSS_AGENT_V6_SERVICE ${GITHUB_RAW_URL}/sss-agent-v6.service >/dev/null 2>&1

    if [[ ! -f $SSS_AGENT_V4_SERVICE || ! -f $SSS_AGENT_V6_SERVICE ]]; then
        echo -e "${red}服务文件下载失败，请确认仓库中存在 sss-agent.service 和 sss-agent-v6.service${plain}"
        return 0
    fi

    if [ $# -lt 3 ]; then
        echo -e "${yellow}请设置 Agent 配置参数：${plain}"
        read -p "服务端域名/IP: " sss_host
        read -p "用户名 (脚本会自动补全 _v4/_v6): " sss_user
        read -p "密码: " sss_pass
    else
        sss_host=$1
        sss_user=$2
        sss_pass=$3
    fi

    # 配置 IPv4 服务
    sed -i "s/sss_host/${sss_host}/" ${SSS_AGENT_V4_SERVICE}
    sed -i "s/sss_user/${sss_user}_v4/" ${SSS_AGENT_V4_SERVICE}
    sed -i "s/sss_pass/${sss_pass}/" ${SSS_AGENT_V4_SERVICE}

    # 配置 IPv6 服务
    sed -i "s/sss_host/${sss_host}/" ${SSS_AGENT_V6_SERVICE}
    sed -i "s/sss_user/${sss_user}_v6/" ${SSS_AGENT_V6_SERVICE}
    sed -i "s/sss_pass/${sss_pass}/" ${SSS_AGENT_V6_SERVICE}

    echo -e "双栈 Agent 配置 ${green}修改成功${plain}"
    systemctl daemon-reload
    systemctl enable sss-agent sss-agent-v6
    systemctl restart sss-agent sss-agent-v6
    echo -e "服务已启动，用户名分别为: ${green}${sss_user}_v4${plain} 和 ${green}${sss_user}_v6${plain}"
}

install_agent() {
    install_base
    echo -e "> 安装监控Agent (IPv4 + IPv6)"
    mkdir -p $SSS_AGENT_PATH
    chmod 777 -R $SSS_AGENT_PATH
    
    echo -e "正在下载监控端脚本..."
    wget --no-check-certificate -qO $SSS_AGENT_PATH/client-linux.py $GITHUB_RAW_URL/client-linux.py
    wget --no-check-certificate -qO $SSS_AGENT_PATH/client-linux-v6.py $GITHUB_RAW_URL/client-linux-v6.py
    
    modify_agent_config "$@"
}

uninstall_agent() {
    echo -e "> 正在卸载监控Agent..."
    systemctl stop sss-agent sss-agent-v6 >/dev/null 2>&1
    systemctl disable sss-agent sss-agent-v6 >/dev/null 2>&1
    rm -rf $SSS_AGENT_PATH
    rm -f $SSS_AGENT_V4_SERVICE $SSS_AGENT_V6_SERVICE
    systemctl daemon-reload
    echo -e "${green}卸载完成${plain}"
}

show_menu() {
    echo -e "
    ${green}Server Status 监控管理脚本 (双栈增强版)${plain}
    --- https://github.com/jscntw/serverstatus ---
    
    ${green}1.${plain}  安装双栈监控Agent (v4 + v6)
    ${green}2.${plain}  卸载Agent
    ${green}0.${plain}  退出脚本
    "
    read -ep "请输入选择 [0-2]: " num
    case "${num}" in
    0)  exit 0 ;; 
    1)  install_agent ;;
    2)  uninstall_agent ;;
    *)  echo -e "${red}请输入正确的数字 [0-2]${plain}" ;;
    esac
}

pre_check
if [[ $# == 3 ]]; then
    uninstall_agent
    install_agent "$@"
else
    show_menu
fi
