#!/bin/bash

mkdir -p "/cloud-model/aiwriting"
mkdir -p "/work/logs/ReportCenterService"

export DEER_FLOW_HOME=/cloud-model/aiwriting
export DEER_FLOW_CONFIG_PATH=/cloud-model/aiwriting/config.yaml

# 设置默认使用 national-security agent
export DEFAULT_AGENT_NAME=national-security

cp -rn agents /cloud-model/aiwriting/
cp -rn skills /cloud-model/aiwriting/
\cp -rf config.yaml /cloud-model/aiwriting/
mkdir logs
cd backend

NO_COLOR=1 uvicorn server:app --host 0.0.0.0 --port 8001
