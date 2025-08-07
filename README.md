# SimpleDiscordRSS
A basic bot to fetch RSS feeds and send them to a Discord channel via webhooks. No limit on feeds, channels, servers. Easy to self host at home or on a remote server. Just a Simple Discord RSS Bot with intuitive Web UI

A lightweight, self-hostable Discord bot that fetches RSS/Atom feeds and posts new entries to your server using webhooks. It comes with a simple, clean web interface for easy management.

<img src="https://github.com/ReverendRetro/SimpleDiscordRSS/blob/main/MainPage.png?raw=true"> 

# Features

- Webhook-Based: Uses Discord webhooks for posting, eliminating the need for bot tokens and complex permissions.

- Web Interface: A simple, multi-page web UI to add, view, and delete feeds from any browser on your network.

- Per-Feed Configuration: Set custom update intervals for each individual feed.

- Initial Post on Add: Immediately fetches and posts the single latest article when a new feed is added to confirm it's working.

- Stateful: Remembers which articles have already been posted to prevent duplicates, even after a restart.

- Lightweight & Efficient: Built with Python and Flask, designed to run efficiently on low-power hardware like a Raspberry Pi or a small VPS.

- Easy to Deploy: Can be run directly with Python or as a persistent service using Gunicorn and systemd.

# Requirements

- A Linux server (e.g., Debian, Ubuntu) or a local machine for hosting.

- Python 3.8+

- pip and venv for managing Python packages.

# Setup & Installation

Follow these steps to get your RSS bot up and running on a Debian-based server.

## 1. Clone the Repository

First, clone this repository to a directory on your server.

`git clone [https://github.com/ReverendRetro/SimpleDiscordRSS](https://github.com/ReverendRetro/SimpleDiscordRSS.git](https://github.com/ReverendRetro/SimpleDiscordRSS.git)`


## 2. Set Up Python Environment

Create a virtual environment to keep the project's dependencies isolated.
### Move into the Directory
`cd SimpleDiscordRSS`

### Create the virtual environment
`python3 -m venv venv`

### Activate it
`source venv/bin/activate`

## 3. Install Dependencies

### Create a requirements.txt file:

`nano requirements.txt`

### Add the following lines to the file:

`feedparser`
`PyYAML`
`Flask`
`gunicorn`
`requests`

Save the file (Ctrl+X, Y, Enter) 

### install the packages:

`pip install -r requirements.txt`

### Get a Discord Webhook URL

You'll need a webhook URL for each channel you want to post to.

- In your Discord server, go to the channel settings (click the ⚙️ icon).

- Navigate to the Integrations tab.

- Click "Create Webhook".

- Give the webhook a name (e.g., "RSS Feeds") and copy the Webhook URL.

### 4. Running the Bot

You can run the bot for testing or set it up as a persistent service.

### To run the bot directly for testing purposes make sure your virtual environment is active
`source venv/bin/activate`

### Run the Flask app
`python main_web.py`

You can then access the web control panel at http://<your_server_ip>:5000.

### As a Persistent Service (Recommended) To ensure the bot runs 24/7 and restarts automatically, set it up as a systemd service.

### Create a service file:

`sudo nano /etc/systemd/system/discord-rss-bot.service`

### Paste the following configuration. Remember to replace your_user with your actual Linux username and update the paths if necessary.

```
[Unit]
Description=Gunicorn instance to serve Discord RSS Bot
After=network.target

[Service]
User=your_user
Group=your_user
WorkingDirectory=/home/your_user/your-repo-name
Environment="PATH=/home/your_user/your-repo-name/venv/bin"
ExecStart=/home/your_user/your-repo-name/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 main_web:app
```

[Install]
WantedBy=multi-user.target`

### Enable and start the service - Reload systemd to recognize the new service
`sudo systemctl daemon-reload`

### Start the service now
`sudo systemctl start discord-rss-bot`

### Enable the service to start automatically on boot
`sudo systemctl enable discord-rss-bot`

### Check the status:

`sudo systemctl status discord-rss-bot`

# 5. Usage

- Once the service is running, navigate to http://<your_server_ip>:5000 in your web browser.

- View Feeds: The main page lists all currently configured RSS feeds.

- Add New Feed: Click "Add New Feed" to go to the form.

- RSS Feed URL: The URL of the RSS/Atom feed you want to monitor.

- Discord Webhook URL: The webhook URL you copied from your Discord channel settings.

- Refresh Interval: How often (in seconds) the bot should check for new articles.

## When you add a new feed, the bot will perform an immediate check to post the single latest article. After that, it will check for all new articles based on the refresh interval you set.

### Configuration Files

The bot automatically creates and manages the following files in the project directory:

- config.json: Stores the list of feeds you've added through the web UI.

- sent_articles.yaml: Acts as the bot's memory, storing a list of article IDs that have already been posted to prevent duplicates.

- feed_state.json: Keeps track of the last time each feed was checked to manage update intervals.

You do not need to edit these files manually.
