#!/bin/bash
# EmotionAI Full-Stack Development Scripts

# Configuration
BACKEND_DIR="."
FRONTEND_DIR="../emotionai-app"  # Adjust path as needed
API_URL="http://localhost:8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Start backend services
start_backend() {
    print_status "Starting backend services..."
    cd "$BACKEND_DIR"
    docker-compose up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check if API is responding
    if curl -f "$API_URL/health" > /dev/null 2>&1; then
        print_success "Backend services are running and healthy!"
    else
        print_warning "Backend services started but API health check failed"
    fi
}

# Stop backend services
stop_backend() {
    print_status "Stopping backend services..."
    cd "$BACKEND_DIR"
    docker-compose down
    print_success "Backend services stopped"
}

# Create test data
create_test_data() {
    print_status "Creating test data..."
    cd "$BACKEND_DIR"
    docker-compose exec api python create_test_data.py
    print_success "Test data created"
}

# Run Flutter app
run_flutter() {
    print_status "Starting Flutter app..."
    if [ -d "$FRONTEND_DIR" ]; then
        cd "$FRONTEND_DIR"
        flutter run
    else
        print_error "Flutter app directory not found: $FRONTEND_DIR"
        print_warning "Please update FRONTEND_DIR in this script"
    fi
}

# Full setup for development
full_setup() {
    print_status "Setting up full development environment..."
    
    # Start backend
    start_backend
    
    # Create test data
    sleep 5
    create_test_data
    
    print_success "Full development environment is ready!"
    print_status "Backend API: $API_URL"
    print_status "Test user: test@emotionai.com / testpass123"
    print_status "Now you can run 'run_flutter' to start the Flutter app"
}

# Show status of all services
show_status() {
    print_status "Development environment status:"
    echo
    
    # Backend services
    cd "$BACKEND_DIR"
    echo "Backend Services:"
    docker-compose ps
    echo
    
    # API health check
    if curl -f "$API_URL/health" > /dev/null 2>&1; then
        print_success "API is responding at $API_URL"
    else
        print_error "API is not responding at $API_URL"
    fi
    echo
    
    # Flutter app check
    if [ -d "$FRONTEND_DIR" ]; then
        print_success "Flutter app directory found: $FRONTEND_DIR"
    else
        print_error "Flutter app directory not found: $FRONTEND_DIR"
    fi
}

# Menu system
show_menu() {
    echo
    echo "EmotionAI Full-Stack Development Helper"
    echo "======================================"
    echo "1. Full Setup (Backend + Test Data)"
    echo "2. Start Backend Only"
    echo "3. Stop Backend"
    echo "4. Create Test Data"
    echo "5. Run Flutter App"
    echo "6. Show Status"
    echo "7. Exit"
    echo
}

# Main script
case "$1" in
    "start")
        start_backend
        ;;
    "stop")
        stop_backend
        ;;
    "setup")
        full_setup
        ;;
    "data")
        create_test_data
        ;;
    "flutter")
        run_flutter
        ;;
    "status")
        show_status
        ;;
    *)
        show_menu
        read -p "Choose an option (1-7): " choice
        case $choice in
            1) full_setup ;;
            2) start_backend ;;
            3) stop_backend ;;
            4) create_test_data ;;
            5) run_flutter ;;
            6) show_status ;;
            7) exit 0 ;;
            *) print_error "Invalid option" ;;
        esac
        ;;
esac