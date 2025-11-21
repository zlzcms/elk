#!/bin/bash

# 自动配置脚本：从父目录的 .env 文件读取 Elasticsearch 密码并更新 Logstash 配置

echo "正在配置 Logstash 连接 Elasticsearch..."

# 选择可用的 .env 文件
PARENT_ENV="../.env"
LOCAL_ENV=".env"
if [ -f "$PARENT_ENV" ]; then
    ENV_FILE="$PARENT_ENV"
elif [ -f "$LOCAL_ENV" ]; then
    ENV_FILE="$LOCAL_ENV"
else
    echo "错误: 未找到 .env 文件: $PARENT_ENV 或 $LOCAL_ENV"
    echo "请手动编辑 logstash/pipeline/logstash.conf 文件配置 Elasticsearch 密码"
    exit 1
fi

# 读取 Elasticsearch 密码
ES_PASSWORD=$(grep "^ELASTIC_PASSWORD=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'")

if [ -z "$ES_PASSWORD" ]; then
    echo "错误: 无法从 .env 文件读取 ELASTIC_PASSWORD"
    exit 1
fi

# 转义特殊字符用于 sed
ES_PASSWORD_ESCAPED=$(echo "$ES_PASSWORD" | sed 's/[[\.*^$()+?{|]/\\&/g')

# 更新 Logstash 配置文件
CONFIG_FILE="logstash/pipeline/logstash.conf"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 未找到配置文件: $CONFIG_FILE"
    exit 1
fi

# 替换密码
sed -i "s/password => \".*\"/password => \"$ES_PASSWORD_ESCAPED\"/" "$CONFIG_FILE"

echo "✓ 已更新 Logstash 配置中的 Elasticsearch 密码"
echo ""
echo "下一步："
echo "1. 检查配置: cat $CONFIG_FILE | grep password"
echo "2. 启动服务: docker compose up -d"
echo "3. 查看日志: docker logs -f logstash"


