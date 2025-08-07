# AWS Deployment Checklist for EmotionAI API

## 🎯 **Deployment Overview**
- **EC2 Instance**: t2.micro (1 vCPU, 1 GB RAM)
- **Database**: RDS PostgreSQL
- **Estimated Cost**: ~$15-25/month

---

## 📋 **Pre-Deployment Tasks**

### **1. AWS Infrastructure Setup**

#### **A. RDS PostgreSQL Database**
- [ ] **Create RDS Instance**
  - Instance class: `db.t3.micro` (free tier eligible)
  - Engine: PostgreSQL 15+
  - Storage: 20 GB (free tier)
  - Multi-AZ: No (for cost savings)
  - Public access: No (security)
  
- [ ] **Security Group for RDS**
  - Name: `emotionai-rds-sg`
  - Inbound: PostgreSQL (5432) from EC2 security group only
  - Outbound: All traffic

- [ ] **Database Configuration**
  - Database name: `emotionai_prod`
  - Username: `emotionai_user`
  - Password: Generate strong password
  - Backup retention: 7 days
  - Maintenance window: Sunday 3-4 AM

#### **B. EC2 Instance**
- [ ] **Launch EC2 Instance**
  - AMI: Ubuntu 22.04 LTS (free tier)
  - Instance type: `t2.micro`
  - Key pair: Create new or use existing
  - Storage: 8 GB (free tier)

- [ ] **Security Group for EC2**
  - Name: `emotionai-api-sg`
  - Inbound rules:
    - SSH (22) from your IP only
    - HTTP (80) from anywhere (0.0.0.0/0)
    - HTTPS (443) from anywhere (0.0.0.0/0)
    - Custom (8000) from anywhere (for testing)
  - Outbound: All traffic

- [ ] **Elastic IP** (optional but recommended)
  - Allocate and associate with EC2 instance
  - Update DNS records if using custom domain

### **2. Code and Configuration Changes**

#### **A. Environment Configuration**
Create `.env.production` on EC2 with:
```bash
# Application
ENVIRONMENT=production
DEBUG=false

# Database - Use RDS endpoint
DATABASE_URL=postgresql://emotionai_user:PASSWORD@your-rds-endpoint:5432/emotionai_prod
DATABASE_POOL_SIZE=5  # Reduced for t2.micro
DATABASE_MAX_OVERFLOW=10

# Security
SECRET_KEY=generate-new-secure-key-32-chars-min
CORS_ORIGINS=["https://yourdomain.com"]  # Update with your domain
TRUSTED_HOSTS=["yourdomain.com"]

# Performance (t2.micro optimizations)
RATE_LIMIT_REQUESTS=50
MAX_MEMORY_ITEMS=50
MAX_ACTIVE_AGENTS=100

# LLM APIs
OPENAI_API_KEY=your_key_here
DEFAULT_LLM_MODEL=gpt-4o-mini  # Cheaper model for testing
```

#### **B. Production Settings Updates**
- [ ] **Update `src/infrastructure/config/settings.py`**
  ```python
  # Add production-specific defaults
  class Settings(BaseSettings):
      # ... existing settings ...
      
      # Production optimizations for t2.micro
      database_pool_size: int = 5 if environment == "production" else 20
      max_active_agents: int = 100 if environment == "production" else 1000
      
      # Enhanced security for production
      enable_https_redirect: bool = True if environment == "production" else False
      
      class Config:
          env_file = ".env.production" if os.getenv("ENVIRONMENT") == "production" else ".env"
  ```

#### **C. Database Connection Optimizations**
- [ ] **Update connection pooling for t2.micro**
  ```python
  # In database/connection.py
  def _get_connect_args(self) -> Dict[str, Any]:
      if "postgresql" in self.settings.database_url:
          return {
              "connect_timeout": 30,
              "pool_timeout": 20,
              "pool_recycle": 3600,  # Recycle connections hourly
              "pool_pre_ping": True   # Verify connections
          }
  ```

### **3. Deployment Scripts**

#### **A. Create deployment script**
- [ ] **Create `deploy.sh`**
  ```bash
  #!/bin/bash
  # deployment script for EC2
  
  # Update system
  sudo apt update && sudo apt upgrade -y
  
  # Install Python 3.11+
  sudo apt install python3.11 python3.11-venv python3-pip git nginx -y
  
  # Clone repository
  git clone YOUR_REPO_URL /opt/emotionai-api
  cd /opt/emotionai-api
  
  # Create virtual environment
  python3.11 -m venv venv
  source venv/bin/activate
  
  # Install dependencies
  pip install -r requirements.txt
  pip install gunicorn uvicorn[standard]
  
  # Copy environment file
  cp .env.production .env
  
  # Run database migrations (when implemented)
  # python migrate.py
  
  # Create systemd service
  sudo cp deployment/emotionai.service /etc/systemd/system/
  sudo systemctl enable emotionai
  sudo systemctl start emotionai
  ```

#### **B. Create systemd service file**
- [ ] **Create `deployment/emotionai.service`**
  ```ini
  [Unit]
  Description=EmotionAI API
  After=network.target
  
  [Service]
  Type=exec
  User=ubuntu
  WorkingDirectory=/opt/emotionai-api
  Environment=PATH=/opt/emotionai-api/venv/bin
  ExecStart=/opt/emotionai-api/venv/bin/gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
  Restart=always
  RestartSec=10
  
  # Resource limits for t2.micro
  MemoryMax=800M
  CPUQuota=80%
  
  [Install]
  WantedBy=multi-user.target
  ```

#### **C. Nginx Configuration**
- [ ] **Create `deployment/nginx.conf`**
  ```nginx
  server {
      listen 80;
      server_name yourdomain.com www.yourdomain.com;
      
      # Redirect HTTP to HTTPS
      return 301 https://$server_name$request_uri;
  }
  
  server {
      listen 443 ssl;
      server_name yourdomain.com www.yourdomain.com;
      
      # SSL certificates (Let's Encrypt recommended)
      ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
      ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
      
      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
          
          # Timeouts
          proxy_connect_timeout 60s;
          proxy_send_timeout 60s;
          proxy_read_timeout 60s;
      }
      
      # Health check endpoint
      location /health {
          proxy_pass http://127.0.0.1:8000/health;
          access_log off;
      }
  }
  ```

### **4. Security Hardening**

#### **A. Application Security**
- [ ] **Update CORS settings**
  ```python
  # Only allow your domain(s)
  CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
  ```

- [ ] **Generate secure secret key**
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- [ ] **Remove debug endpoints in production**
  ```python
  # In main.py
  if not settings.is_production:
      app.include_router(debug_router)  # Only in dev
  ```

#### **B. Infrastructure Security**
- [ ] **EC2 Security**
  - Remove SSH access from 0.0.0.0/0
  - Use key-based authentication only
  - Install fail2ban: `sudo apt install fail2ban`
  - Setup automatic security updates

- [ ] **RDS Security**
  - Encrypt database at rest
  - Use SSL connections
  - Regular security patches
  - No public access

### **5. Monitoring and Logging**

#### **A. Application Monitoring**
- [ ] **CloudWatch Logs**
  ```bash
  # Install CloudWatch agent
  sudo apt install amazon-cloudwatch-agent
  ```

- [ ] **Health Check Monitoring**
  ```python
  # Enhanced health check for production
  @router.get("/health/detailed")
  async def detailed_health():
      return {
          "status": "healthy",
          "database": await check_db_connection(),
          "memory_usage": get_memory_usage(),
          "disk_space": get_disk_usage(),
          "response_time": measure_response_time()
      }
  ```

#### **B. Log Management**
- [ ] **Setup log rotation**
  ```bash
  # /etc/logrotate.d/emotionai
  /opt/emotionai-api/logs/*.log {
      daily
      rotate 30
      compress
      delaycompress
      missingok
      notifempty
      create 644 ubuntu ubuntu
  }
  ```

### **6. Performance Optimizations for t2.micro**

#### **A. Memory Management**
- [ ] **Reduce worker processes**
  ```bash
  # Use only 2 workers for t2.micro
  gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker
  ```

- [ ] **Database connection limits**
  ```python
  DATABASE_POOL_SIZE=3  # Very conservative for t2.micro
  DATABASE_MAX_OVERFLOW=5
  ```

#### **B. Caching Strategy**
- [ ] **Add response caching**
  ```python
  # Simple in-memory cache for static responses
  from functools import lru_cache
  
  @lru_cache(maxsize=100)
  def get_agent_types():
      return cached_agent_types
  ```

#### **C. Resource Monitoring**
- [ ] **Setup swap space** (for memory overflow)
  ```bash
  sudo fallocate -l 1G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```

### **7. SSL/TLS Setup**

#### **A. Let's Encrypt (Free SSL)**
- [ ] **Install Certbot**
  ```bash
  sudo apt install certbot python3-certbot-nginx
  sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
  ```

- [ ] **Auto-renewal setup**
  ```bash
  # Add to crontab
  0 12 * * * /usr/bin/certbot renew --quiet
  ```

### **8. Backup Strategy**

#### **A. Database Backups**
- [ ] **RDS Automated Backups**: Already configured (7 days)
- [ ] **Manual Snapshots**: Before major updates

#### **B. Application Backups**
- [ ] **Code**: Stored in Git repository
- [ ] **Environment Files**: Backup `.env.production` securely
- [ ] **User Data**: Handled by RDS backups

### **9. Domain and DNS**

#### **A. Domain Configuration**
- [ ] **A Record**: Point to EC2 Elastic IP
- [ ] **CNAME Record**: www → main domain
- [ ] **SSL Certificate**: Let's Encrypt setup

#### **B. API Documentation**
- [ ] **Public Docs**: `https://yourdomain.com/docs`
- [ ] **Health Check**: `https://yourdomain.com/health`

---

## 🚀 **Deployment Steps**

### **Phase 1: Infrastructure**
1. ✅ Create RDS PostgreSQL instance
2. ✅ Launch EC2 t2.micro instance
3. ✅ Configure security groups
4. ✅ Allocate Elastic IP

### **Phase 2: Application**
1. ✅ SSH to EC2 instance
2. ✅ Run deployment script
3. ✅ Configure environment variables
4. ✅ Start application service

### **Phase 3: Web Server**
1. ✅ Configure Nginx
2. ✅ Setup SSL with Let's Encrypt
3. ✅ Test HTTPS access

### **Phase 4: Monitoring**
1. ✅ Verify health checks
2. ✅ Setup CloudWatch logs
3. ✅ Test application functionality

---

## 💰 **Cost Estimation (Monthly)**

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| EC2 t2.micro | 1 vCPU, 1GB RAM | $8.50 |
| RDS db.t3.micro | PostgreSQL | $12.00 |
| EBS Storage | 20GB | $2.00 |
| Data Transfer | < 1GB | $0.50 |
| **Total** | | **~$23/month** |

*Note: Costs may vary based on usage and region*

---

## 🔧 **Quick Commands Reference**

```bash
# Check application status
sudo systemctl status emotionai

# View logs
sudo journalctl -u emotionai -f

# Restart application
sudo systemctl restart emotionai

# Check database connection
psql -h your-rds-endpoint -U emotionai_user -d emotionai_prod

# Monitor resources
htop
free -h
df -h

# SSL certificate renewal
sudo certbot renew

# Update application
cd /opt/emotionai-api
git pull
sudo systemctl restart emotionai
```

---

## ⚠️ **Important Notes**

1. **t2.micro Limitations**: 
   - 1 CPU credit per minute
   - Burst performance when needed
   - Monitor CPU credits in CloudWatch

2. **Database Connections**: 
   - Limit concurrent connections
   - Use connection pooling efficiently

3. **Memory Management**: 
   - Monitor memory usage closely
   - Setup swap space for overflow

4. **Security**: 
   - Never commit `.env.production` to git
   - Use IAM roles instead of hardcoded AWS keys
   - Regular security updates

5. **Monitoring**: 
   - Setup CloudWatch alarms for high CPU/memory
   - Monitor database connections
   - Setup uptime monitoring

---

This checklist should get your EmotionAI API running smoothly on AWS! 🚀