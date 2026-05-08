FROM python:3.9-alpine
LABEL maintainer="jscntw"

# 安装基础依赖
RUN pip install --no-cache-dir requests

# 设置工作目录
WORKDIR /app

# 复制脚本到镜像
COPY ./bot.py .

# 设置时区（可选，建议设为上海）
ENV TZ=Asia/Shanghai

CMD [ "python", "./bot.py" ]
