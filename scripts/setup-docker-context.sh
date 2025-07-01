#!/bin/bash

# Setup Docker context for testing
# This script configures Docker to use the colima-arm context for ARM-based testing

echo "Setting up Docker context for testing..."

# Check if colima-arm context exists
if docker context ls | grep -q "colima-arm"; then
    echo "✅ colima-arm context found"
    
    # Switch to colima-arm context
    docker context use colima-arm
    echo "✅ Switched to colima-arm context"
    
    # Unset DOCKER_HOST to avoid override warnings
    unset DOCKER_HOST
    echo "✅ Unset DOCKER_HOST environment variable"
    
    # Verify the active context
    echo "📋 Current Docker context:"
    docker context ls | grep "\*"
    
    echo ""
    echo "🚀 Docker context is now ready for testing!"
    echo "   You can now run tests with: python -m pytest tests/"
    
else
    echo "❌ colima-arm context not found!"
    echo "   Please make sure Colima ARM profile is set up:"
    echo "   1. Install Colima: brew install colima"
    echo "   2. Create ARM profile: colima start --profile arm --arch aarch64"
    echo "   3. Re-run this script"
    exit 1
fi 