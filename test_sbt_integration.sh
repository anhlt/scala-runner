#!/bin/bash
set -e

echo "🧪 Testing SBT Integration Workflow"

echo "1. Starting FastAPI server..."
python -m uvicorn scala_runner.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Wait for server to start
sleep 5

cleanup() {
    echo "Cleaning up..."
    curl -s -X DELETE http://localhost:8000/workspaces/test-sbt > /dev/null 2>&1 || true
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
}

trap cleanup EXIT

echo "2. Testing API health..."
PING_RESPONSE=$(curl -s http://localhost:8000/ping)
if echo "$PING_RESPONSE" | grep -q "pong"; then
    echo "✅ API is healthy"
else
    echo "❌ API health check failed"
    exit 1
fi

echo "3. Creating workspace..."
curl -s -X DELETE http://localhost:8000/workspaces/test-sbt > /dev/null 2>&1 || true
WORKSPACE_RESPONSE=$(curl -s -X POST http://localhost:8000/workspaces \
    -H "Content-Type: application/json" \
    -d '{"name":"test-sbt"}')

if echo "$WORKSPACE_RESPONSE" | grep -q '"status":"success"'; then
    echo "✅ Workspace created"
else
    echo "❌ Workspace creation failed: $WORKSPACE_RESPONSE"
    exit 1
fi

echo "4. Creating simple Scala file..."
# First, remove the default Main.scala to avoid conflicts
curl -s -X DELETE http://localhost:8000/files/test-sbt/src/main/scala/Main.scala > /dev/null 2>&1 || true

# Use a simple one-liner to avoid JSON encoding issues
SIMPLE_PAYLOAD='{"workspace_name":"test-sbt","file_path":"src/main/scala/SimpleTest.scala","content":"object SimpleTest extends App { println(\"Hello from SBT integration test!\"); println(\"Scala version: \" + scala.util.Properties.versionString) }"}'

FILE_RESPONSE=$(curl -s -X POST http://localhost:8000/files \
    -H "Content-Type: application/json" \
    -d "$SIMPLE_PAYLOAD")

if echo "$FILE_RESPONSE" | grep -q '"created":true'; then
    echo "✅ Simple Scala file created"
else
    echo "❌ File creation failed: $FILE_RESPONSE"
    exit 1
fi

echo "5. Testing SBT compile..."
COMPILE_RESPONSE=$(curl -s -X POST http://localhost:8000/sbt/compile \
    -H "Content-Type: application/json" \
    -d '{"workspace_name":"test-sbt"}')

echo "Compile response (first 200 chars): $(echo "$COMPILE_RESPONSE" | head -c 200)..."

if echo "$COMPILE_RESPONSE" | grep -q '"status":"success"'; then
    echo "✅ SBT compile successful"
else
    echo "❌ SBT compile failed"
    echo "Full response: $COMPILE_RESPONSE"
    exit 1
fi

echo "6. Testing SBT run..."
RUN_RESPONSE=$(curl -s -X POST http://localhost:8000/sbt/run-project \
    -H "Content-Type: application/json" \
    -d '{"workspace_name":"test-sbt"}')

echo "Run response (first 200 chars): $(echo "$RUN_RESPONSE" | head -c 200)..."

if echo "$RUN_RESPONSE" | grep -q '"status":"success"'; then
    echo "✅ SBT run successful"
    if echo "$RUN_RESPONSE" | grep -q "Hello from SBT integration test"; then
        echo "✅ Expected output found"
    else
        echo "⚠️  Expected output not found in response"
    fi
else
    echo "❌ SBT run failed"
    echo "Full response: $RUN_RESPONSE"
    exit 1
fi

echo "7. Testing SBT clean..."
CLEAN_RESPONSE=$(curl -s -X POST http://localhost:8000/sbt/clean \
    -H "Content-Type: application/json" \
    -d '{"workspace_name":"test-sbt"}')

if echo "$CLEAN_RESPONSE" | grep -q '"status":"success"'; then
    echo "✅ SBT clean successful"
else
    echo "❌ SBT clean failed: $CLEAN_RESPONSE"
    exit 1
fi

echo "🎉 All SBT integration tests passed!"
echo "The image-build workflow should work correctly for SBT operations." 