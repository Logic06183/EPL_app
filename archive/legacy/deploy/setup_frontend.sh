#!/bin/bash

# FPL Prediction Frontend Setup Script

echo "🚀 Setting up FPL Prediction Frontend..."
echo "======================================"

# Check if we're in the right directory
if [ ! -f "package.json" ] && [ ! -d "frontend" ]; then
    echo "❌ Error: Run this script from the main project directory"
    exit 1
fi

# Navigate to frontend directory
cd frontend

echo "📦 Installing dependencies..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "🎉 Frontend setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the backend API:"
echo "   cd .."  
echo "   python run.py"
echo ""
echo "2. In another terminal, start the frontend:"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "3. Open your browser to:"
echo "   🌐 Frontend: http://localhost:3000"
echo "   📡 API: http://localhost:8000"
echo "   📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Happy coding! 🎯"