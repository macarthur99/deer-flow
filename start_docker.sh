#!/usr/bin/env bash

# 设置日志目录（可选，但建议日志走 stdout）
mkdir -p "/cloud-model/aiwriting"
mkdir -p "/cloud-model/aiwriting/skills"
mkdir -p "/work/logs/ReportCenterService"
mkdir -p "/work/bin/ReportCenterService/backend/.langgraph_api"

export DEER_FLOW_HOME=/cloud-model/aiwriting
export DEER_FLOW_CONFIG_PATH=/cloud-model/aiwriting/config.yaml
export DEFAULT_AGENT_NAME=national-security

\cp -rf agents /cloud-model/aiwriting/
cp -rn skills/* /cloud-model/aiwriting/skills
#\cp -rf skills/* /cloud-model/aiwriting/skills
#cp -rn config.yaml /cloud-model/aiwriting/
\cp -rf config.yaml /cloud-model/aiwriting/

# 切换目录
cd backend
# 直接前台运行 Uvicorn，不使用 &，不重定向到文件
# 使用 --log-config 可自定义日志格式（可选）
exec uvicorn server:app \
  --host 0.0.0.0 \
  --port 8001 \
  --workers 1
