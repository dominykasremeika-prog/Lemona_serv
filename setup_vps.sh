#!/bin/bash

# Lemona LED Matrix Server - VPS Setup Script
# Run this script as root on your Ubuntu/Debian VPS

set -e

echo "Starting Lemona Server Setup..."

# 1. Update System and Install Dependencies
echo "Updating system packages..."
apt-get update
apt-get install -y python3-pip python3-venv nginx git

# 2. Setup Application Directory
APP_DIR="/opt/lemona_serv"
echo "Setting up application directory at $APP_DIR..."

# Create directory if it doesn't exist
mkdir -p $APP_DIR

# Copy current directory contents to APP_DIR (assuming script is run from the repo)
# We use rsync or cp. Here we assume the user uploaded the files to a temp folder or cloned git.
# If running from within the uploaded folder:
cp -r . $APP_DIR

cd $APP_DIR

# 3. Setup Python Virtual Environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure Systemd Service
echo "Configuring Systemd service..."
cp deploy/lemona.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload
systemctl start lemona
systemctl enable lemona

# 5. Configure Nginx
echo "Configuring Nginx..."
cp deploy/nginx_lemona /etc/nginx/sites-available/lemona

# Ask for Domain or IP
read -p "Enter your VPS IP address or Domain Name (e.g., 192.168.1.100 or example.com): " SERVER_NAME

if [ ! -z "$SERVER_NAME" ]; then
    sed -i "s/server_name _;/server_name $SERVER_NAME;/g" /etc/nginx/sites-available/lemona
fi

# Enable the site
ln -sf /etc/nginx/sites-available/lemona /etc/nginx/sites-enabled
rm -f /etc/nginx/sites-enabled/default

# Test and Restart Nginx
nginx -t
systemctl restart nginx

# 6. Firewall Setup (Optional but recommended)
echo "Configuring Firewall (UFW)..."
if command -v ufw > /dev/null; then
    ufw allow 'Nginx Full'
    ufw allow ssh
    # ufw enable # Uncomment if you want to enable ufw automatically (be careful not to lock yourself out)
fi

echo "------------------------------------------------"
echo "Setup Complete!"
echo "Your server should be accessible at http://$SERVER_NAME"
echo "------------------------------------------------"
