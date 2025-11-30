# Deployment Guide

This guide explains how to deploy the Lemona LED Matrix Server to a VPS (Virtual Private Server) running Ubuntu or Debian.

## Prerequisites

*   A VPS running Ubuntu 20.04/22.04 or Debian 10/11.
*   Root access (or sudo privileges) to the server.
*   The project files uploaded to the server.

## Deployment Steps

1.  **Upload Files**:
    Copy the entire project folder to your VPS. You can use `scp` or `git`.
    
    *Example using SCP:*
    ```bash
    scp -r /path/to/Lemona_serv root@<your-vps-ip>:~/Lemona_serv
    ```

2.  **SSH into Server**:
    ```bash
    ssh root@<your-vps-ip>
    ```

3.  **Run Setup Script**:
    Navigate to the uploaded folder and run the setup script.
    
    ```bash
    cd ~/Lemona_serv
    chmod +x setup_vps.sh
    sudo ./setup_vps.sh
    ```

4.  **Follow Prompts**:
    The script will ask for your Domain Name or IP Address. Enter it when prompted.

5.  **Access the Site**:
    Open your browser and go to `http://<your-vps-ip>`.

## Manual Configuration (If needed)

*   **Service Status**: Check if the app is running.
    ```bash
    systemctl status lemona
    ```
*   **Nginx Status**: Check web server status.
    ```bash
    systemctl status nginx
    ```
*   **Logs**:
    *   App logs: `journalctl -u lemona`
    *   Nginx logs: `/var/log/nginx/error.log`

## Updating the App

If you make changes to the code:

1.  Upload the new files to `/opt/lemona_serv`.
2.  Restart the service:
    ```bash
    sudo systemctl restart lemona
    ```
