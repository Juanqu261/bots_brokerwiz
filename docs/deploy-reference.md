# BrokerWiz - Deployment Quick Reference

## Daily Operations

### Start Services
```bash
./scripts/api.sh start -d        # Start API in background
./scripts/worker.sh start        # Start workers (uses .env config)
```

### Stop Services
```bash
./scripts/worker.sh stop         # Stop all workers
./scripts/api.sh stop            # Stop API
```

### Check Status
```bash
./scripts/worker.sh status       # Full status report
./scripts/api.sh status          # API status only
curl http://localhost:8000/health  # Health check
```

### View Logs
```bash
./scripts/api.sh logs            # API logs (tail -f)
./scripts/worker.sh logs         # All worker logs
./scripts/worker.sh logs worker-1  # Specific worker
tail -f logs/mosquitto.log       # MQTT broker logs
```

### Scale Workers
```bash
./scripts/worker.sh scale 5      # Scale to 5 workers
./scripts/worker.sh start -n 3 -b 4  # 3 workers × 4 bots each
```

## Deployment

### Automated (GitHub Actions)
```bash
# Just push to main branch
git push origin main

# GitHub Actions will:
# 1. Run tests
# 2. Deploy to server
# 3. Run health checks
# 4. Rollback if failed
```

### Manual Deployment
```bash
cd /opt/brokerwiz
./scripts/deploy.sh              # Deploy from main
./scripts/deploy.sh dev          # Deploy from dev branch
```

### Rollback
```bash
./scripts/deploy.sh rollback     # Rollback to previous commit
```

### Deployment Status
```bash
./scripts/deploy.sh status       # View deployment info
```

## Troubleshooting

### API Not Responding
```bash
# Check if running
./scripts/api.sh status

# Check logs
./scripts/api.sh logs

# Restart
./scripts/api.sh restart -d

# Check port
sudo netstat -tlnp | grep 8000
```

### Workers Not Processing Jobs
```bash
# Check worker status
./scripts/worker.sh status

# Check worker logs
./scripts/worker.sh logs

# Check MQTT broker
./scripts/mosquitto.sh healthcheck

# Restart workers
./scripts/worker.sh restart
```

### High Memory Usage
```bash
# Check Chrome processes
pgrep -a chrome | wc -l

# Check memory
free -h

# Reduce concurrent bots
./scripts/worker.sh stop
./scripts/worker.sh start -n 2 -b 2  # 2 workers × 2 bots = 4 Chrome max
```

### Disk Space Issues
```bash
# Check disk usage
df -h

# Clean old logs
find logs/ -name "*.log.*" -mtime +7 -delete

# Clean temp files
rm -rf temp/pdfs/*
rm -rf temp/profiles/*/cookies.json
```

### MQTT Connection Issues
```bash
# Check Mosquitto status
sudo systemctl status mosquitto

# Restart Mosquitto
sudo systemctl restart mosquitto

# Check MQTT logs
tail -f logs/mosquitto.log

# Test MQTT connection
./scripts/mosquitto.sh test
```

## Monitoring

### Real-Time Monitoring
```bash
# Watch worker status
watch -n 5 './scripts/worker.sh status'

# Monitor system resources
htop

# Monitor Chrome processes
watch -n 2 'pgrep -a chrome | wc -l'
```

### Check Alerts
```bash
# View alert log
tail -f logs/alerts.log

# View health monitor log
tail -f logs/health_monitor.log
```

### Metrics
```bash
# API metrics
curl http://localhost:8000/metrics

# MQTT broker stats
./scripts/mosquitto.sh healthcheck
```

## Maintenance

### Update Dependencies
```bash
cd /opt/brokerwiz
source .venv/bin/activate
pip install -r requirements.txt --upgrade
./scripts/api.sh restart -d
./scripts/worker.sh restart
```

### Rotate Logs Manually
```bash
# Compress old logs
gzip logs/*.log.2026-*

# Delete logs older than 30 days
find logs/ -name "*.log.*.gz" -mtime +30 -delete
```

### Backup Configuration
```bash
# Backup .env
cp .env .env.backup.$(date +%Y%m%d)

# Backup entire config
tar -czf backup-$(date +%Y%m%d).tar.gz .env config/ scripts/
```

### Clean Temp Files
```bash
# Clean PDFs older than 7 days
find temp/pdfs/ -name "*.pdf" -mtime +7 -delete

# Clean old profiles
find temp/profiles/ -type d -mtime +30 -exec rm -rf {} +
```

## Security

### Update API Key
```bash
# Generate new key
openssl rand -hex 32

# Update .env
nano .env  # Update API_KEY

# Restart API
./scripts/api.sh restart -d
```

### Renew SSL Certificate
```bash
# Certbot auto-renews, but to force:
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

### Check Firewall
```bash
# View rules
sudo ufw status

# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

## Performance Tuning

### For 4GB RAM VM
```bash
# .env configuration
NUM_WORKERS=1
MAX_CONCURRENT_BOTS=2
# Total: 2 Chrome instances max
```

### For 8GB RAM VM
```bash
# .env configuration
NUM_WORKERS=2
MAX_CONCURRENT_BOTS=3
# Total: 6 Chrome instances max
```

### For 16GB RAM VM
```bash
# .env configuration
NUM_WORKERS=3
MAX_CONCURRENT_BOTS=4
# Total: 12 Chrome instances max
```

## GitHub Actions Setup

### Required Secrets
Add these in GitHub repository settings → Secrets and variables → Actions:

```
SSH_PRIVATE_KEY    # Private SSH key for deployment user
DEPLOY_USER        # SSH username (e.g., brokerwiz)
DEPLOY_HOST        # Server IP or domain
DEPLOY_PATH        # Path to project (e.g., /opt/brokerwiz)
```

### Generate SSH Key
```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/brokerwiz_deploy

# Copy public key to server
ssh-copy-id -i ~/.ssh/brokerwiz_deploy.pub user@server

# Add private key to GitHub secrets
cat ~/.ssh/brokerwiz_deploy  # Copy this to SSH_PRIVATE_KEY secret
```

## Emergency Procedures

### Complete Service Restart
```bash
./scripts/worker.sh stop
./scripts/api.sh stop
sudo systemctl restart mosquitto
sleep 5
./scripts/api.sh start -d
./scripts/worker.sh start
```

### Emergency Rollback
```bash
cd /opt/brokerwiz
git log --oneline -5  # Find previous commit
git reset --hard <commit-hash>
./scripts/api.sh restart -d
./scripts/worker.sh restart
```

### Kill All Chrome Processes
```bash
# If Chrome processes are stuck
pkill -9 chrome
pkill -9 chromium

# Then restart workers
./scripts/worker.sh restart
```

## Useful Commands

```bash
# Check what's listening on ports
sudo netstat -tlnp | grep -E ':(8000|1883|80|443)'

# Check process tree
pstree -p | grep -E '(uvicorn|python|chrome)'

# Monitor network connections
sudo ss -tunap | grep -E ':(8000|1883)'

# Check system load
uptime
cat /proc/loadavg

# Check memory by process
ps aux --sort=-%mem | head -10

# Check disk I/O
iostat -x 1 5
```

## Contact & Support

- **Logs Location**: `/opt/brokerwiz/logs/`
- **Config Location**: `/opt/brokerwiz/.env`
- **Nginx Config**: `/etc/nginx/sites-available/brokerwiz`
- **Cron Config**: `/etc/cron.d/brokerwiz-health`

For issues, check logs first:
```bash
./scripts/worker.sh status
./scripts/api.sh logs
tail -f logs/alerts.log
```
