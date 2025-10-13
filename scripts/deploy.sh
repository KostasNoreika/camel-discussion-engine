#!/bin/bash
set -e

echo "🚀 Deploying CAMEL Discussion Engine"

# Check environment
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production not found"
    exit 1
fi

# Validate API keys
if ! grep -q "OPENROUTER_API_KEY=sk-or-v1-" .env.production; then
    echo "❌ Error: OPENROUTER_API_KEY not set in .env.production"
    exit 1
fi

# Build Docker image
echo "📦 Building Docker image..."
docker-compose -f docker-compose.production.yml build

# Stop existing container
echo "🛑 Stopping existing container..."
docker-compose -f docker-compose.production.yml down || true

# Start new container
echo "▶️  Starting new container..."
docker-compose -f docker-compose.production.yml up -d

# Wait for health check
echo "🏥 Waiting for health check..."
sleep 10

# Test health endpoint
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    docker-compose -f docker-compose.production.yml logs --tail=50
    exit 1
fi

# Show status
docker-compose -f docker-compose.production.yml ps

echo "✅ Deployment complete!"
echo "🌐 API available at: https://camel.noreika.lt"
echo "📊 Health: https://camel.noreika.lt/health"
