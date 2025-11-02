#!/bin/bash

# AI Agent Kernel Docker Management Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env
    print_warning "Please edit .env file with your API keys before running the services."
fi

# Start services
start_services() {
    print_status "Starting AI Agent Kernel services..."
    docker-compose up -d
    print_status "Services started!"
    print_status "Application: http://localhost:8000"
    print_status "API Documentation: http://localhost:8000/docs"
}

# Stop services
stop_services() {
    print_status "Stopping AI Agent Kernel services..."
    docker-compose down
    print_status "Services stopped!"
}

# Restart services
restart_services() {
    print_status "Restarting AI Agent Kernel services..."
    docker-compose restart
    print_status "Services restarted!"
}

# View logs
view_logs() {
    docker-compose logs -f
}

# Build images
build_images() {
    print_status "Building Docker images..."
    docker-compose build
    print_status "Images built successfully!"
}

# Clean up
cleanup() {
    print_status "Cleaning up Docker containers and volumes..."
    docker-compose down -v --remove-orphans
    docker system prune -f
    print_status "Cleanup completed!"
}

# Show status
status() {
    print_status "Service Status:"
    docker-compose ps
}

# Install dependencies
install_deps() {
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    print_status "Dependencies installed!"
}

# Run tests
run_tests() {
    print_status "Running system tests..."
    python test_system.py
}

# Show help
show_help() {
    echo "AI Agent Kernel Docker Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start all services"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  status    Show service status"
    echo "  logs      View service logs"
    echo "  build     Build Docker images"
    echo "  cleanup   Clean up containers and volumes"
    echo "  deps      Install Python dependencies"
    echo "  test      Run system tests"
    echo "  help      Show this help message"
    echo ""
    echo "Environment Setup:"
    echo "  1. Copy .env.example to .env"
    echo "  2. Add your API keys to .env"
    echo "  3. Run: $0 deps"
    echo "  4. Run: $0 start"
}

# Main script logic
case "${1:-help}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        view_logs
        ;;
    build)
        build_images
        ;;
    cleanup)
        cleanup
        ;;
    deps)
        install_deps
        ;;
    test)
        run_tests
        ;;
    status)
        status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac