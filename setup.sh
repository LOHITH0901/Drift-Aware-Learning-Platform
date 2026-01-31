#!/bin/bash
echo "🚀 Setting up Drift-Aware Learning Platform..."

# 1. Install Dependencies
echo "📦 Installing Python libraries..."
pip install -r requirements.txt
pip install requests watchdog

# 2. Check Ollama
if ! command -v ollama &> /dev/null
then
    echo "⚠️  Ollama is not installed. Please install it from https://ollama.com/"
    exit 1
fi

echo "🧠 Pulling AI Model (Phi-3)..."
ollama pull phi3:mini

echo "✅ Setup Complete! Run ./start.sh to launch."
