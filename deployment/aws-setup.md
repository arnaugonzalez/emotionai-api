# AWS Infrastructure Setup Guide

This guide helps you set up the AWS infrastructure for EmotionAI API deployment.

## Prerequisites

1. AWS CLI installed and configured
2. AWS account with appropriate permissions
3. Domain name (optional but recommended)

## Quick Setup Commands

### 1. Create Security Groups

```bash
# Create security group for RDS
aws ec2 create-security-group \
    --group-name emotionai-rds-sg \
    --description "Security group for EmotionAI RDS database"

# Get the RDS security group ID
RDS_SG_ID=$(aws ec2 describe-security-groups \
    --group-names emotionai-rds-sg \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

# Create security group for EC2
aws ec2 create-security-group \
    --group-name emotionai-api-sg \
    --description "Security group for EmotionAI API server"

# Get the EC2 security group ID
EC2_SG_ID=$(aws ec2 describe-security-groups \
    --group-names emotionai-api-sg \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

# Configure RDS security group (PostgreSQL from EC2 only)
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $EC2_SG_ID

# Configure EC2 security group
# SSH access (replace with your IP)
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr YOUR_IP_ADDRESS/32

# HTTP access
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

# HTTPS access
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

# API port for testing (remove in production)
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0
```

### 2. Create RDS Database

```bash
# Create DB subnet group (you'll need subnet IDs from your VPC)
aws rds create-db-subnet-group \
    --db-subnet-group-name emotionai-subnet-group \
    --db-subnet-group-description "Subnet group for EmotionAI database" \
    --subnet-ids subnet-xxxxxxxx subnet-yyyyyyyy

# Create RDS PostgreSQL instance
aws rds create-db-instance \
    --db-instance-identifier emotionai-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username emotionai_user \
    --master-user-password "YOUR_SECURE_PASSWORD" \
    --allocated-storage 20 \
    --storage-type gp2 \
    --vpc-security-group-ids $RDS_SG_ID \
    --db-subnet-group-name emotionai-subnet-group \
    --backup-retention-period 7 \
    --storage-encrypted \
    --no-multi-az \
    --no-publicly-accessible \
    --db-name emotionai_prod
```

### 3. Launch EC2 Instance

```bash
# Create key pair (if you don't have one)
aws ec2 create-key-pair \
    --key-name emotionai-key \
    --query 'KeyMaterial' \
    --output text > emotionai-key.pem
chmod 400 emotionai-key.pem

# Launch EC2 instance
aws ec2 run-instances \
    --image-id ami-0c7217cdde317cfec \
    --count 1 \
    --instance-type t2.micro \
    --key-name emotionai-key \
    --security-group-ids $EC2_SG_ID \
    --user-data file://user-data.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=EmotionAI-API}]'

# Get instance ID
INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=EmotionAI-API" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text)

# Allocate Elastic IP
aws ec2 allocate-address \
    --domain vpc \
    --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=EmotionAI-EIP}]'

# Get Elastic IP allocation ID
EIP_ALLOC_ID=$(aws ec2 describe-addresses \
    --filters "Name=tag:Name,Values=EmotionAI-EIP" \
    --query 'Addresses[0].AllocationId' \
    --output text)

# Associate Elastic IP with instance
aws ec2 associate-address \
    --instance-id $INSTANCE_ID \
    --allocation-id $EIP_ALLOC_ID
```

### 4. User Data Script for EC2

Create `user-data.sh`:

```bash
#!/bin/bash
apt update
apt install -y python3.11 python3.11-venv git nginx
useradd -m -s /bin/bash emotionai
usermod -aG sudo emotionai
```

## Manual Setup Steps

### 1. Get RDS Endpoint
```bash
aws rds describe-db-instances \
    --db-instance-identifier emotionai-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text
```

### 2. Get EC2 Public IP
```bash
aws ec2 describe-addresses \
    --filters "Name=tag:Name,Values=EmotionAI-EIP" \
    --query 'Addresses[0].PublicIp' \
    --output text
```

### 3. Connect to EC2
```bash
# Get the public IP first
PUBLIC_IP=$(aws ec2 describe-addresses \
    --filters "Name=tag:Name,Values=EmotionAI-EIP" \
    --query 'Addresses[0].PublicIp' \
    --output text)

# SSH to the instance
ssh -i emotionai-key.pem ubuntu@$PUBLIC_IP
```

## CloudFormation Template (Alternative)

You can also use the CloudFormation template in `aws-cloudformation.yaml` for automated setup.

```bash
aws cloudformation create-stack \
    --stack-name emotionai-infrastructure \
    --template-body file://aws-cloudformation.yaml \
    --parameters ParameterKey=KeyName,ParameterValue=your-key-name \
                ParameterKey=YourIP,ParameterValue=YOUR_IP_ADDRESS/32
```

## Cost Monitoring

Set up billing alerts:

```bash
# Create SNS topic for billing alerts
aws sns create-topic --name emotionai-billing-alerts

# Subscribe to the topic
aws sns subscribe \
    --topic-arn arn:aws:sns:us-east-1:ACCOUNT-ID:emotionai-billing-alerts \
    --protocol email \
    --notification-endpoint your-email@example.com
```

## Next Steps

1. Wait for RDS instance to be available (5-10 minutes)
2. SSH to EC2 instance
3. Run the deployment script: `./deployment/deploy.sh`
4. Configure environment variables
5. Start the application

## Useful Commands

```bash
# Check RDS status
aws rds describe-db-instances --db-instance-identifier emotionai-db

# Check EC2 status
aws ec2 describe-instances --filters "Name=tag:Name,Values=EmotionAI-API"

# Get connection information
echo "RDS Endpoint: $(aws rds describe-db-instances --db-instance-identifier emotionai-db --query 'DBInstances[0].Endpoint.Address' --output text)"
echo "EC2 Public IP: $(aws ec2 describe-addresses --filters "Name=tag:Name,Values=EmotionAI-EIP" --query 'Addresses[0].PublicIp' --output text)"
```