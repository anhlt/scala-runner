#!/bin/bash
set -e

echo "🧪 Testing Integration Workflow Steps"

echo "0. Cleaning up any existing workspace..."
# Clean up any existing test workspace first
curl -s -X DELETE http://localhost:8000/workspaces/test-integration > /dev/null 2>&1 || true

echo "1. Starting FastAPI server..."
python -m uvicorn scala_runner.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Wait for server to start
sleep 5

echo "2. Testing ping endpoint..."
PING_RESPONSE=$(curl -s http://localhost:8000/ping)
echo "Ping response: $PING_RESPONSE"

if echo "$PING_RESPONSE" | grep -q "pong"; then
    echo "✅ Ping test passed"
else
    echo "❌ Ping test failed"
    kill $SERVER_PID
    exit 1
fi

echo "3. Cleaning up any existing workspace..."
curl -s -X DELETE http://localhost:8000/workspaces/test-integration > /dev/null 2>&1 || true

echo "4. Testing workspace creation..."
WORKSPACE_RESPONSE=$(curl -s -X POST http://localhost:8000/workspaces \
    -H "Content-Type: application/json" \
    -d '{"name":"test-integration"}')
echo "Workspace response: $WORKSPACE_RESPONSE"

if echo "$WORKSPACE_RESPONSE" | grep -q '"status":"success"'; then
    echo "✅ Workspace creation test passed"
else
    echo "❌ Workspace creation test failed"
    kill $SERVER_PID
    exit 1
fi

echo "5. Testing file creation..."
# Use a simple one-liner to avoid JSON encoding issues
PAYLOAD=$(cat << 'EOF'
{
  "workspace_name": "test-integration",
  "file_path": "src/main/scala/HelloWorld.scala",
  "content": "object HelloWorld extends App { println(\"Hello from integration test!\") }"
}
EOF
)

FILE_RESPONSE=$(curl -s -X POST http://localhost:8000/files \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

echo "File creation response: $FILE_RESPONSE"

if echo "$FILE_RESPONSE" | grep -q '"created":true'; then
    echo "✅ File creation test passed"
else
    echo "❌ File creation test failed"
    kill $SERVER_PID
    exit 1
fi

echo "6. Cleaning up..."
curl -s -X DELETE http://localhost:8000/workspaces/test-integration > /dev/null

echo "7. Stopping server..."
kill $SERVER_PID
wait $SERVER_PID 2>/dev/null || true

echo "🎉 All integration tests passed! The workflow should work correctly." 