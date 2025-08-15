#!/bin/bash

# Production deployment script for FPL AI Pro
# Optimized for South African hosting providers

set -e

echo "🚀 Starting FPL AI Pro Production Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="fpl-ai-pro"
IMAGE_TAG=${1:-latest}
DOCKER_REGISTRY=${DOCKER_REGISTRY:-""}

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Setup environment
setup_environment() {
    log_info "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        log_warning ".env file not found, creating template..."
        cat > .env << EOF
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key_here

# Redis Configuration
REDIS_URL=redis://redis:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database (optional)
DATABASE_URL=postgresql://user:password@localhost:5432/fplai

# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# Deployment
ENVIRONMENT=production
DEBUG=false
EOF
        log_warning "Please update .env file with your actual configuration before deploying"
        read -p "Press enter to continue once you've updated .env..."
    fi
    
    log_success "Environment setup complete"
}

# Build frontend
build_frontend() {
    log_info "Building frontend..."
    
    cd frontend
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        npm install
    fi
    
    # Build for production
    log_info "Building frontend for production..."
    npm run build
    
    cd ..
    log_success "Frontend build complete"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    # Build production API image
    docker build -f Dockerfile.production -t ${PROJECT_NAME}-api:${IMAGE_TAG} .
    
    log_success "Docker images built successfully"
}

# Deploy with Docker Compose
deploy() {
    log_info "Deploying with Docker Compose..."
    
    # Stop existing containers
    docker-compose -f docker-compose.production.yml down
    
    # Start new deployment
    docker-compose -f docker-compose.production.yml up -d
    
    log_success "Deployment complete"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Wait for services to start
    sleep 10
    
    # Check API health
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null; then
            log_success "API is healthy"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_error "API health check failed"
            exit 1
        fi
        
        log_info "Waiting for API to start... (attempt $i/30)"
        sleep 2
    done
    
    # Check frontend
    if curl -s http://localhost:80 > /dev/null; then
        log_success "Frontend is accessible"
    else
        log_warning "Frontend might not be accessible"
    fi
}

# Display deployment info
show_deployment_info() {
    log_success "🎉 Deployment completed successfully!"
    echo ""
    echo "📊 Service Status:"
    docker-compose -f docker-compose.production.yml ps
    echo ""
    echo "🌐 Access URLs:"
    echo "  Frontend: http://localhost"
    echo "  API: http://localhost/api"
    echo "  API Docs: http://localhost/api/docs"
    echo "  Health Check: http://localhost/health"
    echo ""
    echo "📝 Useful Commands:"
    echo "  View logs: docker-compose -f docker-compose.production.yml logs -f"
    echo "  Stop services: docker-compose -f docker-compose.production.yml down"
    echo "  Restart services: docker-compose -f docker-compose.production.yml restart"
    echo ""
    echo "💳 Payment Integration:"
    echo "  Update your Stripe keys in .env file"
    echo "  Test payments with Stripe test cards"
    echo ""
    echo "🇿🇦 South African Optimizations:"
    echo "  ✅ Redis caching enabled"
    echo "  ✅ Gzip compression enabled"
    echo "  ✅ CDN-ready static assets"
    echo "  ✅ Optimized timeout settings"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up old Docker images..."
    docker image prune -f
}

# Main deployment flow
main() {
    log_info "🇿🇦 FPL AI Pro - South Africa Optimized Deployment"
    echo "=============================================="
    
    check_prerequisites
    setup_environment
    build_frontend
    build_images
    deploy
    health_check
    show_deployment_info
    cleanup
    
    log_success "✅ All done! Your FPL AI Pro application is now running."
}

# Handle interruption
trap 'log_error "Deployment interrupted"; exit 1' INT

# Run main function
main "$@"