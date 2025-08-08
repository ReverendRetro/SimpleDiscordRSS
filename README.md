# SimpleDiscordRSS
A basic bot to fetch RSS feeds and send them to a Discord channel via webhooks. No limit on feeds, channels, servers. Easy to self host at home or on a remote server. Just a Simple Discord RSS Bot with intuitive Web UI

A lightweight, self-hostable Discord bot that fetches RSS/Atom feeds and posts new entries to your server using webhooks. It comes with a simple, clean web interface for easy management.

<img src="https://github.com/ReverendRetro/SimpleDiscordRSS/blob/main/MainPage-1.png?raw=true"> 

# Features

- Webhook-Based: Uses Discord webhooks for posting, eliminating the need for bot tokens and complex permissions.

- Web Interface: A simple, multi-page web UI to add, view, and delete feeds from any browser on your network.

- Per-Feed Configuration: Set custom update intervals for each individual feed.

- Initial Post on Add: Immediately fetches and posts the single latest article when a new feed is added to confirm it's working.

- Stateful: Remembers which articles have already been posted to prevent duplicates, even after a restart.

- Lightweight & Efficient: Built with Python and Flask, designed to run efficiently on low-power hardware like a Raspberry Pi or a small VPS.

- Easy to Deploy: Can be run directly with Python or as a persistent service using Gunicorn and systemd.

# Requirements

- A Linux server (e.g., Debian, Ubuntu) or a local machine for hosting. Also should work on Windows and MacOS but I am unsure how to test there.

- Python 3.8+

- pip and venv for managing Python packages.

# Setup & Installation
Follow these steps to get your RSS bot up and running on a Debian-based server.

## 1. Clone this repository to a directory on your server.

`git clone [https://github.com/ReverendRetro/SimpleDiscordRSS](https://github.com/ReverendRetro/SimpleDiscordRSS.git](https://github.com/ReverendRetro/SimpleDiscordRSS.git)`

Ensure you have the following files in your project directory (e.g., /home/your_user/discord-rss-bot): <br>
main_web.py (The web interface) <br>
scheduler.py (The background feed checker)

## 2. Set Up Python Environment
Create a virtual environment to keep the project's dependencies isolated.

### Navigate to your project directory
`cd /path/to/your/discord-rss-bot`

### Ensure needed deps are installed
`sudo apt install python3 python3-venv python3-pip -y`

### Create the virtual environment
`python3 -m venv venv`

### Activate it
`source venv/bin/activate`


## 3. Install Dependencies
Create a requirements.txt file:
`nano requirements.txt`

# Add the following lines to the file:
```
feedparser
PyYAML
Flask
gunicorn
requests
```

Save the file (Ctrl+X, Y, Enter) and then install the packages:
`pip install -r requirements.txt`


## 4. Get a Discord Webhook URL
You'll need a webhook URL for each channel you want to post to.
- In your Discord server, go to the channel settings (click the ⚙️ icon).
- Navigate to the Integrations tab.
- Click "Create Webhook".
- Give the webhook a name (e.g., "RSS Feeds") and copy the Webhook URL.


## 5. Running the Bot as a Service (Recommended)
To ensure the bot runs 24/7 and restarts automatically, we will set up two separate systemd services: one for the web UI and one for the scheduler.
## 1. Create the Web UI Service
Create a service file for the Gunicorn web server.
`sudo nano /etc/systemd/system/discord-rss-web.service`


Paste the following configuration. Remember to replace your_user with your actual Linux username and update the paths if necessary.
```
[Unit]
Description=Gunicorn instance to serve Discord RSS Bot Web UI
After=network.target

[Service]
User=your_user
Group=your_user
WorkingDirectory=/home/your_user/discord-rss-bot
Environment="PATH=/home/your_user/discord-rss-bot/venv/bin"
ExecStart=/home/your_user/discord-rss-bot/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 "main_web:app"
Restart=always

[Install]
WantedBy=multi-user.target
```

## 6. Create the Scheduler Service
Create a second service file for the background scheduler.
`sudo nano /etc/systemd/system/discord-rss-scheduler.service`


Paste the following configuration, again replacing your_user and the paths.
```
[Unit]
Description=Scheduler for Discord RSS Bot
After=network.target

[Service]
User=your_user
Group=your_user
WorkingDirectory=/home/your_user/discord-rss-bot
ExecStart=/home/your_user/discord-rss-bot/venv/bin/python scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 7. Enable and Start the Services
Now, tell systemd to recognize, enable, and start your new services.
### Reload systemd to recognize the new service files
`sudo systemctl daemon-reload`

### Enable and start the web UI service
`sudo systemctl enable discord-rss-web.service`
`sudo systemctl start discord-rss-web.service`

### Enable and start the scheduler service
`sudo systemctl enable discord-rss-scheduler.service`
`sudo systemctl start discord-rss-scheduler.service`


### Check the Status
You can check the status of each service independently:
`sudo systemctl status discord-rss-web.service`
`sudo systemctl status discord-rss-scheduler.service`

Check for errors:
`sudo journalctl -u discord-rss-scheduler -n 50 --no-pager`
`sudo systemctl start discord-rss-web -n 50 --no-pager`


The scheduler log should show "Scheduler started." and "Scheduler running check..." messages.

## 8. Usage
Once the services are running, navigate to http://<your_server_ip>:5000 in your web browser.

- View Feeds: The main page lists all currently configured RSS feeds.

- Add New Feed: Click "Add New Feed" to go to the form.

- RSS Feed URL: The URL of the RSS/Atom feed you want to monitor.

- Discord Webhook URL: The webhook URL you copied from your Discord channel settings.

- Refresh Interval: How often (in seconds) the bot should check for new articles.

- Edit Feed: Click the "Edit" link next to any feed to modify its settings.

- The scheduler will automatically pick up any new or edited feeds on its next cycle (within 60 seconds).

# Configuration Files
The bot automatically creates and manages the following files in the project directory:
- config.json: Stores the list of feeds you've added through the web UI.
- sent_articles.yaml: Acts as the bot's memory, storing a list of article IDs that have already been posted to prevent duplicates.
- feed_state.json: Keeps track of the last time each feed was checked to manage update intervals.
You do not need to edit these files manually.
