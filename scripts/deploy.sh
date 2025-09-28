#!/bin/bash

# Production Deployment Script for Financial Advisor AI
# This script handles deployment to a fresh production environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="advisor-ai"
PROJECT_DIR="/opt/$PROJECT_NAME"
BACKUP_DIR="/opt/backups/$PROJECT_NAME"
LOG_FILE="/var/log/$PROJECT_NAME-deploy.log"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
    fi
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check if Git is installed
    if ! command -v git &> /dev/null; then
        error "Git is not installed. Please install Git first."
    fi
    
    # Check available disk space (at least 10GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 10485760 ]; then  # 10GB in KB
        warning "Low disk space detected. At least 10GB recommended."
    fi
    
    log "System requirements check passed"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package list
    sudo apt-get update
    
    # Install required packages
    sudo apt-get install -y \
        curl \
        wget \
        unzip \
        htop \
        ufw \
        fail2ban \
        certbot \
        python3-certbot-nginx
    
    log "System dependencies installed"
}

# Setup firewall
setup_firewall() {
    log "Setting up firewall..."
    
    # Enable UFW
    sudo ufw --force enable
    
    # Allow SSH
    sudo ufw allow ssh
    
    # Allow HTTP and HTTPS
    sudo ufw allow 80
    sudo ufw allow 443
    
    # Allow application ports (if not using reverse proxy)
    sudo ufw allow 3000
    sudo ufw allow 8000
    
    log "Firewall configured"
}

# Setup fail2ban
setup_fail2ban() {
    log "Setting up fail2ban..."
    
    # Create fail2ban jail for nginx
    sudo tee /etc/fail2ban/jail.d/nginx.conf > /dev/null <<EOF
[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
EOF
    
    # Restart fail2ban
    sudo systemctl restart fail2ban
    
    log "Fail2ban configured"
}

# Create project directory
setup_project_directory() {
    log "Setting up project directory..."
    
    # Create project directory
    sudo mkdir -p "$PROJECT_DIR"
    sudo chown $USER:$USER "$PROJECT_DIR"
    
    # Create backup directory
    sudo mkdir -p "$BACKUP_DIR"
    sudo chown $USER:$USER "$BACKUP_DIR"
    
    # Create log file
    sudo touch "$LOG_FILE"
    sudo chown $USER:$USER "$LOG_FILE"
    
    log "Project directory created: $PROJECT_DIR"
}

# Clone or update repository
setup_repository() {
    log "Setting up repository..."
    
    cd "$PROJECT_DIR"
    
    if [ -d ".git" ]; then
        log "Updating existing repository..."
        git pull origin main
    else
        log "Cloning repository..."
        git clone https://github.com/your-username/$PROJECT_NAME.git .
    fi
    
    log "Repository setup complete"
}

# Setup environment files
setup_environment() {
    log "Setting up environment files..."
    
    cd "$PROJECT_DIR"
    
    # Create production environment file if it doesn't exist
    if [ ! -f "backend/.env.production" ]; then
        log "Creating production environment file..."
        cat > backend/.env.production <<EOF
# Production Environment Configuration
ENVIRONMENT=production
DEBUG=false

# Database Configuration
POSTGRES_DB=advisor_ai
POSTGRES_USER=advisor_user
POSTGRES_PASSWORD=CHANGE_ME_SECURE_PASSWORD

# Redis Configuration
REDIS_URL=redis://redis:6379

# JWT Configuration
JWT_SECRET_KEY=CHANGE_ME_JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-domain.com/api/v1/auth/google/callback

# HubSpot OAuth Configuration
HUBSPOT_CLIENT_ID=your_hubspot_client_id
HUBSPOT_CLIENT_SECRET=your_hubspot_client_secret
HUBSPOT_REDIRECT_URI=https://your-domain.com/api/v1/auth/hubspot/callback

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Frontend Configuration
REACT_APP_API_URL=https://your-domain.com/api

# CORS Configuration
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
EOF
        warning "Please update backend/.env.production with your actual configuration values"
    fi
    
    log "Environment files configured"
}

# Deploy application
deploy_application() {
    log "Deploying application..."
    
    cd "$PROJECT_DIR"
    
    # Pull latest images
    log "Pulling latest Docker images..."
    docker-compose -f docker-compose.prod.yml pull
    
    # Stop existing containers
    log "Stopping existing containers..."
    docker-compose -f docker-compose.prod.yml down || true
    
    # Start services
    log "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        error "Backend service is not healthy"
    fi
    
    if ! curl -f http://localhost:3000/health > /dev/null 2>&1; then
        error "Frontend service is not healthy"
    fi
    
    log "Application deployed successfully"
}

# Setup SSL certificates
setup_ssl() {
    log "Setting up SSL certificates..."
    
    # This would typically be done with Let's Encrypt
    # For now, we'll create self-signed certificates for testing
    sudo mkdir -p /etc/nginx/ssl
    
    if [ ! -f "/etc/nginx/ssl/cert.pem" ]; then
        log "Creating self-signed SSL certificate..."
        sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /etc/nginx/ssl/key.pem \
            -out /etc/nginx/ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    fi
    
    log "SSL certificates configured"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create systemd service for the application
    sudo tee /etc/systemd/system/$PROJECT_NAME.service > /dev/null <<EOF
[Unit]
Description=Financial Advisor AI Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable and start the service
    sudo systemctl daemon-reload
    sudo systemctl enable $PROJECT_NAME.service
    
    log "Monitoring configured"
}

# Create backup script
create_backup_script() {
    log "Creating backup script..."
    
    sudo tee /usr/local/bin/backup-$PROJECT_NAME.sh > /dev/null <<EOF
#!/bin/bash
# Backup script for $PROJECT_NAME

BACKUP_DIR="$BACKUP_DIR"
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\$BACKUP_DIR/backup_\$DATE.tar.gz"

# Create backup
cd "$PROJECT_DIR"
tar -czf "\$BACKUP_FILE" \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='*.log' \
    .

# Keep only last 7 days of backups
find "\$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup created: \$BACKUP_FILE"
EOF
    
    sudo chmod +x /usr/local/bin/backup-$PROJECT_NAME.sh
    
    # Add to crontab for daily backups
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-$PROJECT_NAME.sh") | crontab -
    
    log "Backup script created"
}

# Main deployment function
main() {
    log "Starting deployment of Financial Advisor AI..."
    
    check_root
    check_requirements
    install_dependencies
    setup_firewall
    setup_fail2ban
    setup_project_directory
    setup_repository
    setup_environment
    setup_ssl
    deploy_application
    setup_monitoring
    create_backup_script
    
    log "Deployment completed successfully!"
    log "Application is running at: http://localhost"
    log "Backend API: http://localhost:8000"
    log "Frontend: http://localhost:3000"
    log "Logs: $LOG_FILE"
    
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Update backend/.env.production with your actual configuration"
    echo "2. Restart services: sudo systemctl restart $PROJECT_NAME"
    echo "3. Setup SSL certificates with Let's Encrypt"
    echo "4. Configure your domain DNS to point to this server"
    echo "5. Test the application thoroughly"
}

# Run main function
main "$@"