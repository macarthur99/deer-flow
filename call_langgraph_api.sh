#!/bin/bash

# 第一步：创建thread并获取thread_id
echo "=== 步骤1: 创建thread ==="
CREATE_THREAD_URL="http://192.168.82.122:8001/ReportCenterService/rest/gateway/api/user"
CREATE_THREAD_DATA='{
    "generalArgument": {
      "userId": 12234
    },
    "jsonArg": {}
  }'

# 调用创建thread接口
RESPONSE=$(curl -s -X POST "$CREATE_THREAD_URL" \
  -H "Content-Type: application/json" \
  -d "$CREATE_THREAD_DATA")

echo "创建thread响应:"
echo "$RESPONSE" | jq '.'

# 提取thread_id
THREAD_ID=$(echo "$RESPONSE" | jq -r '.thread_id')

if [ -z "$THREAD_ID" ] || [ "$THREAD_ID" = "null" ]; then
    echo "错误: 无法提取thread_id"
    exit 1
fi

echo "提取到的thread_id: $THREAD_ID"
echo ""

# 第二步：调用对话接口
echo "=== 步骤2: 调用对话接口 ==="
CHAT_URL="http://192.168.82.122:8001/ReportCenterService/rest/langgraph/threads/${THREAD_ID}/runs/stream"

CHAT_DATA=$(cat <<EOF
{
  "input": {
    "messages": [
      {
        "type": "human",
        "content": [
          {
            "type": "text",
            "text": "解析中美芯片科技差距"
          }
        ]
      }
    ]
  },
  "config": {
    "recursion_limit": 1000
  },
  "context": {
    "model_name": "deepseek-v3",
    "mode": "ultra",
    "thinking_enabled": true,
    "is_plan_mode": true,
    "subagent_enabled": true,
    "thread_id": "$THREAD_ID",
    "user_id": "346"
  },
  "stream_mode": [
    "values",
    "messages-tuple",
    "custom",
    "updates"
  ],
  "stream_subgraphs": true,
  "stream_resumable": true,
  "assistant_id": "lead_agent",
  "on_disconnect": "continue"
}
EOF
)

echo "调用对话接口..."
curl -X POST "$CHAT_URL" \
  -H "Content-Type: application/json" \
  -d "$CHAT_DATA"

echo ""
echo "=== 完成 ==="
