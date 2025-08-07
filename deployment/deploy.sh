#!/bin/bash
# EmotionAI API Deployment Script for AWS EC2
# Run this script on your EC2 instance to deploy the application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="emotionai-api"
APP_DIR="/opt/$APP_NAME"
APP_USER="ubuntu"
PYTHON_VERSION="3.11"
REPO_URL="https://github.com/YOUR_USERNAME/emotionai-api.git"  # Update this!

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root. Run as ubuntu user."
fi

log "Starting EmotionAI API deployment..."

# Update system packages
log "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
log "Installing system dependencies..."
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    git \
    nginx \
    curl \
    wget \
    htop \
    tree \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    postgresql-client-15 \
    redis-tools \
    fail2ban \
    ufw

# Configure firewall
log "Configuring UFW firewall..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw allow 8000  # For testing, remove in production

# Install Python dependencies globally needed
log "Installing global Python packages..."
sudo pip3 install --upgrade pip setuptools wheel

# Create application directory
log "Setting up application directory..."
sudo mkdir -p $APP_DIR
sudo chown $APP_USER:$APP_USER $APP_DIR

# Clone repository
log "Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
    log "Repository already exists, pulling latest changes..."
    cd $APP_DIR
    git pull origin main
else
    git clone $REPO_URL $APP_DIR
    cd $APP_DIR
fi

# Create Python virtual environment
log "Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip in virtual environment
log "Upgrading pip in virtual environment..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
log "Installing Python dependencies..."
if [ -f "requirements-production.txt" ]; then
    pip install -r requirements-production.txt
else
    pip install -r requirements.txt
    # Install additional production packages
    pip install gunicorn uvicorn[standard] psycopg2-binary boto3
fi

# Copy environment template
log "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.production.template" ]; then
        cp .env.production.template .env
        warn "Environment file created from template. Please update .env with your actual values!"
    else
        warn "No .env file found. Please create one with your configuration."
    fi
fi

# Set up systemd service
log "Setting up systemd service..."
sudo cp deployment/emotionai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable emotionai

# Set up Nginx
log "Configuring Nginx..."
sudo cp deployment/nginx.conf /etc/nginx/sites-available/emotionai

# Remove default nginx site and enable our site
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/emotionai /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Set up log directories
log "Setting up logging directories..."
sudo mkdir -p /var/log/emotionai
sudo chown $APP_USER:$APP_USER /var/log/emotionai

# Set up log rotation
log "Setting up log rotation..."
sudo tee /etc/logrotate.d/emotionai > /dev/null <<EOF
/var/log/emotionai/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload emotionai
    endscript
}
EOF

# Set up swap space (important for t2.micro)
log "Setting up swap space..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    log "1GB swap space created and activated"
else
    log "Swap space already exists"
fi

# Configure fail2ban for SSH protection
log "Configuring fail2ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Create a simple health check script
log "Creating health check script..."
tee $APP_DIR/health_check.sh > /dev/null <<EOF
#!/bin/bash
# Simple health check script
curl -f http://localhost:8000/health || exit 1
EOF
chmod +x $APP_DIR/health_check.sh

# Set up database management scripts
log "Setting up database management..."
chmod +x create_schema.py
chmod +x manage_db.py

# Create database setup script
tee $APP_DIR/setup_database.sh > /dev/null <<EOF
#!/bin/bash
# Database setup script for EmotionAI API

echo "🏥 Setting up EmotionAI Database..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it first."
    exit 1
fi

# Check database connection
echo "📡 Testing database connection..."
python3 -c "
import asyncio
import sys
sys.path.insert(0, 'src')
from src.infrastructure.config.settings import settings
from src.infrastructure.database.connection import DatabaseConnection

async def test():
    try:
        db = await DatabaseConnection.create(settings)
        print('✅ Database connection successful!')
        await db.close()
        return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

result = asyncio.run(test())
if not result:
    exit(1)
"

if [ \$? -ne 0 ]; then
    echo "❌ Database connection failed. Please check your configuration."
    exit 1
fi

# Create database schema
echo "🏗️  Creating database schema..."
python3 create_schema.py create

if [ \$? -eq 0 ]; then
    echo "✅ Database setup completed successfully!"
    echo "📊 Database information:"
    python3 create_schema.py info
else
    echo "❌ Database setup failed!"
    exit 1
fi
EOF
chmod +x $APP_DIR/setup_database.sh

# Install AWS CLI (useful for CloudWatch logs)
log "Installing AWS CLI..."
if ! command -v aws &> /dev/null; then
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    rm -rf awscliv2.zip aws/
fi

# Create deployment info file
log "Creating deployment info..."
tee $APP_DIR/deployment_info.txt > /dev/null <<EOF
EmotionAI API Deployment Information
===================================
Deployment Date: $(date)
Python Version: $(python3.11 --version)
Git Commit: $(git rev-parse HEAD)
Git Branch: $(git branch --show-current)
Server: $(hostname)
OS: $(lsb_release -d | cut -f2)

Service Status:
- Application: sudo systemctl status emotionai
- Nginx: sudo systemctl status nginx

Useful Commands:
- View logs: sudo journalctl -u emotionai -f
- Restart app: sudo systemctl restart emotionai
- Test nginx: sudo nginx -t
- Reload nginx: sudo systemctl reload nginx

Health Check:
- Local: curl http://localhost:8000/health
- External: curl https://yourdomain.com/health
EOF

# Set proper permissions
log "Setting file permissions..."
sudo chown -R $APP_USER:$APP_USER $APP_DIR
chmod +x $APP_DIR/deployment/deploy.sh

log "Deployment script completed successfully!"
echo
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Update .env file with your actual configuration values"
echo "2. Set up database: ./setup_database.sh"
echo "3. Update domain name in /etc/nginx/sites-available/emotionai"
echo "4. Set up SSL with: sudo certbot --nginx -d yourdomain.com"
echo "5. Start the application: sudo systemctl start emotionai"
echo "6. Start nginx: sudo systemctl start nginx"
echo "7. Check status: sudo systemctl status emotionai"
echo "8. Test the API: curl https://yourdomain.com/health"
echo "9. Verify database: python3 manage_db.py info"
echo
echo -e "${GREEN}Deployment ready! Don't forget to configure your environment variables.${NC}"