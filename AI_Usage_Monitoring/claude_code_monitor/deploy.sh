#!/bin/bash
# Claude Code Monitor - VPS Deployment Script
# Usage: ./deploy.sh [version_tag]

set -e

DEPLOY_DIR="/home/claude-code-monitor"
REPO_URL="https://github.com/e-gmat/GitHub-System.git"
SUBFOLDER="AI_Usage_Monitoring/claude_code_monitor"

echo "============================================================"
echo "Claude Code Monitor - Deployment"
echo "============================================================"

cd "$DEPLOY_DIR"

# Check if this is initial setup or update
if [ ! -d ".git" ]; then
    echo "Initial setup - cloning repository..."
    cd /tmp
    rm -rf github-system-clone
    git clone --depth 1 --filter=blob:none --sparse "$REPO_URL" github-system-clone
    cd github-system-clone
    git sparse-checkout set "$SUBFOLDER"

    # Copy files to deploy directory
    cp -r "$SUBFOLDER/"* "$DEPLOY_DIR/"
    cd "$DEPLOY_DIR"
    rm -rf /tmp/github-system-clone
else
    echo "Updating from repository..."
    git fetch origin main

    if [ -n "$1" ]; then
        echo "Checking out tag: $1"
        git checkout "$1"
    else
        git pull origin main
    fi
fi

# Setup virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Install/update dependencies
echo "Installing dependencies..."
./venv/bin/pip install -r requirements.txt --quiet

# Check .env configuration
if [ ! -f "config/.env" ]; then
    echo ""
    echo "WARNING: config/.env not found!"
    echo "Please copy config/.env.example to config/.env and configure:"
    echo "  cp config/.env.example config/.env"
    echo "  nano config/.env"
fi

# Restart service if running
if systemctl is-active --quiet claude-code-monitor; then
    echo "Restarting service..."
    sudo systemctl restart claude-code-monitor
    echo "Service restarted"
else
    echo ""
    echo "Service not running. To start:"
    echo "  sudo systemctl start claude-code-monitor"
fi

echo ""
echo "============================================================"
echo "Deployment complete!"
echo "============================================================"

# Show current version
if [ -f "VERSION" ]; then
    echo "Version: $(cat VERSION)"
fi
echo "Deployed at: $(date)"
