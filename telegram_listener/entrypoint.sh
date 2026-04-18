#!/bin/bash

# Ensure environment variables are available to cron jobs
# We exclude some restricted variables and save the rest to /etc/environment
printenv | grep -v "no_proxy" >> /etc/environment

# Start the cron daemon
service cron start

# Run the main bot listener in the foreground
echo "[*] Starting Telegram Bot Listener and Cron Scheduler..."
exec python main.py
