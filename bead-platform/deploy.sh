#!/bin/bash

# BEAD Platform Deployment Script
# This script sets up and deploys the BEAD platform locally

set -e

echo "🚀 Starting BEAD Platform Deployment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing."
    echo "   Press Enter to continue with default values, or Ctrl+C to exit."
    read -r || true
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down || true

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up --build -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
docker-compose ps

# Run database migrations if needed
echo "🗄️  Ensuring database is properly initialized..."
docker-compose exec -T db psql -U postgres -d bead -c "SELECT version();" > /dev/null

if [ $? -eq 0 ]; then
    echo "✅ Database is ready!"
else
    echo "❌ Database connection failed!"
    exit 1
fi

# Test API
echo "🧪 Testing API..."
sleep 5
if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✅ API is responding!"
else
    echo "⚠️  API might not be ready yet. Check logs with: docker-compose logs api"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📋 Services available at:"
echo "   • API: http://localhost:8000"
echo "   • API Docs: http://localhost:8000/docs"
echo "   • Web App: http://localhost:3000 (if web service is configured)"
echo "   • Database: localhost:5432"
echo ""
echo "📊 To view logs: docker-compose logs -f [service-name]"
echo "🛑 To stop: docker-compose down"
echo "🔄 To restart: docker-compose restart"