# 介绍
项目基于cppla版本ServerStatus， 增加如下功能：

- 更方便的节点管理, 支持增删改查
- 上下线通知（telegram）
- Agent机器安装脚本改为systemd， 支持开机自启

# 安装
在**服务端**复制以下命令，一键到底。请记得替换成你自己的YOUR_TG_CHAT_ID和YOUR_TG_BOT_TOKEN。

其中，Bot token可以通过@BotFather创建机器人获取， Chat id可以通过@getuserID获取。
```
mkdir -p /opt/stacks/sss
cd /opt/stacks/sss

cd /opt/stacks

直接获取你的全家桶运行 
wget -N --no-check-certificate https://raw.githubusercontent.com/jscntw/chr-serverstatus/master/sss.sh
chmod +x sss.sh
# 格式：./sss.sh "你的CHAT_ID" "你的BOT_TOKEN"
./sss.sh 

```


# 参考
- https://github.com/cppla/ServerStatus
- https://github.com/naiba/nezha
- https://github.com/lidalao/ServerStatus
----------

