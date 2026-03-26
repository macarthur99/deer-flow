#!/usr/bin/env python3
"""Quick test script for the runs API."""
import requests
import json

BASE_URL = "http://localhost:8001"
THREAD_ID = "test-thread-001"

def test_stream_run():
    """Test streaming conversation endpoint."""
    url = f"{BASE_URL}/api/threads/{THREAD_ID}/runs/stream"
    payload = {
        "input": {
            "messages": [{"role": "human", "content": "Hello, what's 2+2?"}]
        },
        "stream_mode": ["values", "messages-tuple"]
    }

    print(f"Testing: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")

    response = requests.post(url, json=payload, stream=True)
    print(f"Status: {response.status_code}")
    print("Events:")

    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))

def test_get_history():
    """Test getting conversation history."""
    url = f"{BASE_URL}/api/threads/{THREAD_ID}/history"

    print(f"\nTesting: GET {url}")
    response = requests.get(url)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Thread ID: {data['thread_id']}")
        print(f"Title: {data.get('title')}")
        print(f"Messages: {len(data['messages'])}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    print("=== DeerFlow Runs API Test ===\n")
    test_stream_run()
    test_get_history()
