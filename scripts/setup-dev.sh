#!/bin/bash

# Development Setup Script for Financial Advisor AI
# This script sets up the development environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="advisor-ai"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check if Docker is installed
check_docker() {
    log "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker."
    fi
    
    log "Docker is installed and running"
}

# Setup backend environment
setup_backend() {
    log "Setting up backend environment..."
    
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    log "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        log "Creating backend .env file..."
        cat > .env <<EOF
# Development Environment Configuration
ENVIRONMENT=development
DEBUG=true

# Database Configuration
DATABASE_URL=postgresql://advisor_user:advisor_password@localhost:5432/advisor_ai

# Redis Configuration
REDIS_URL=redis://localhost:6379

# JWT Configuration
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth Configuration (Add your actual values)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# HubSpot OAuth Configuration (Add your actual values)
HUBSPOT_CLIENT_ID=your_hubspot_client_id
HUBSPOT_CLIENT_SECRET=your_hubspot_client_secret
HUBSPOT_REDIRECT_URI=http://localhost:8000/api/v1/auth/hubspot/callback

# OpenAI Configuration (Add your actual API key)
OPENAI_API_KEY=your_openai_api_key

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
EOF
        warning "Please update backend/.env with your actual configuration values"
    fi
    
    cd ..
    log "Backend environment setup complete"
}

# Setup frontend environment
setup_frontend() {
    log "Setting up frontend environment..."
    
    cd frontend
    
    # Install dependencies
    log "Installing Node.js dependencies..."
    npm install
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        log "Creating frontend .env file..."
        cat > .env <<EOF
# Frontend Environment Configuration
REACT_APP_API_URL=http://localhost:8000
GENERATE_SOURCEMAP=false
EOF
    fi
    
    cd ..
    log "Frontend environment setup complete"
}

# Start development services
start_services() {
    log "Starting development services..."
    
    # Start database and Redis with Docker Compose
    log "Starting PostgreSQL and Redis..."
    docker-compose up -d postgres redis
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 10
    
    # Check if services are running
    if ! docker-compose ps postgres | grep -q "Up"; then
        error "PostgreSQL failed to start"
    fi
    
    if ! docker-compose ps redis | grep -q "Up"; then
        error "Redis failed to start"
    fi
    
    log "Development services started successfully"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    cd backend
    source venv/bin/activate
    
    # Run Alembic migrations
    if command -v alembic &> /dev/null; then
        alembic upgrade head
    else
        warning "Alembic not found. Please install it or run migrations manually."
    fi
    
    cd ..
    log "Database migrations completed"
}

# Create useful scripts
create_scripts() {
    log "Creating development scripts..."
    
    # Backend start script
    cat > start-backend.sh <<EOF
#!/bin/bash
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
EOF
    chmod +x start-backend.sh
    
    # Frontend start script
    cat > start-frontend.sh <<EOF
#!/bin/bash
cd frontend
npm start
EOF
    chmod +x start-frontend.sh
    
    # Stop services script
    cat > stop-services.sh <<EOF
#!/bin/bash
docker-compose down
EOF
    chmod +x stop-services.sh
    
    log "Development scripts created"
}

# Main setup function
main() {
    log "Setting up Financial Advisor AI development environment..."
    
    check_docker
    setup_backend
    setup_frontend
    start_services
    run_migrations
    create_scripts
    
    log "Development environment setup complete!"
    
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Update backend/.env with your actual API keys and configuration"
    echo "2. Update frontend/.env if needed"
    echo "3. Start the backend: ./start-backend.sh"
    echo "4. Start the frontend: ./start-frontend.sh"
    echo "5. Visit http://localhost:3000 to see the application"
    echo ""
    echo -e "${GREEN}Useful commands:${NC}"
    echo "- Stop services: ./stop-services.sh"
    echo "- View logs: docker-compose logs -f"
    echo "- Restart services: docker-compose restart"
}

# Run main function
main "$@"