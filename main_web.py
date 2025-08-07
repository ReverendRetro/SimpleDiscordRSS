# main_web.py
# A Discord RSS bot with a multi-page web interface for configuration.
# This version uses webhooks and allows editing of existing feeds.

import os
import asyncio
import feedparser
import yaml
import json
import threading
import uuid
import requests
from datetime import datetime, timezone
from flask import Flask, render_template_string, request, redirect, url_for, flash, get_flashed_messages
from werkzeug.serving import is_running_from_reloader

# --- Set a common User-Agent for all feedparser requests ---
feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0"

# --- Flask Web App Setup ---
app = Flask(__name__)
app.secret_key = os.urandom(24) # Required for flashing messages

# --- Configuration & State Files ---
CONFIG_FILE = "config.json"
SENT_ARTICLES_FILE = "sent_articles.yaml"
FEED_STATE_FILE = "feed_state.json"

# --- Global variable to hold the scheduler thread ---
scheduler_instance = None

# --- HTML Templates ---

LAYOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Discord RSS Bot Control Panel</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; } </style>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📡</text></svg>">
</head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto p-4 md:p-8 max-w-4xl">
        <h1 class="text-3xl font-bold mb-2 text-center">Discord RSS Bot Control Panel</h1>
        
        <nav class="flex justify-center space-x-6 bg-gray-800 p-4 rounded-xl shadow-lg mb-6">
            <a href="{{ url_for('view_feeds') }}" class="text-gray-300 hover:text-white transition-colors">View Feeds</a>
            <a href="{{ url_for('add_feed') }}" class="text-gray-300 hover:text-white transition-colors">Add New Feed</a>
        </nav>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                <div class="bg-{{ 'green' if category == 'success' else 'red' }}-500/20 border border-{{ 'green' if category == 'success' else 'red' }}-500 text-{{ 'green' if category == 'success' else 'red' }}-300 px-4 py-3 rounded-lg relative mb-6" role="alert">
                    <span class="block sm:inline">{{ message }}</span>
                </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <main>
            {% block content %}{% endblock %}
        </main>
    </div>
</body>
</html>
"""

VIEW_FEEDS_TEMPLATE = """
<div class="bg-gray-800 p-6 rounded-xl shadow-lg">
    <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-semibold">Existing Feeds</h2>
        <a href="{{ url_for('add_feed') }}" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition-colors duration-200">
            Add New Feed
        </a>
    </div>
    <div class="overflow-x-auto">
        <table class="min-w-full text-left text-sm font-light">
            <thead class="border-b border-gray-600 font-medium">
                <tr>
                    <th scope="col" class="px-6 py-4">Feed URL</th>
                    <th scope="col" class="px-6 py-4">Webhook URL</th>
                    <th scope="col" class="px-6 py-4">Interval (s)</th>
                    <th scope="col" class="px-6 py-4">Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for feed in config.FEEDS %}
                <tr class="border-b border-gray-700">
                    <td class="px-6 py-4 font-mono text-xs truncate" style="max-width: 250px;">{{ feed.url }}</td>
                    <td class="px-6 py-4 font-mono text-xs truncate" style="max-width: 250px;">{{ feed.webhook_url }}</td>
                    <td class="px-6 py-4">{{ feed.update_interval }}</td>
                    <td class="px-6 py-4 flex items-center space-x-4">
                        <a href="{{ url_for('edit_feed', feed_id=feed.id) }}" class="text-indigo-400 hover:text-indigo-300">Edit</a>
                        <form action="{{ url_for('delete_feed', feed_id=feed.id) }}" method="post" onsubmit="return confirm('Are you sure you want to delete this feed?');">
                            <button type="submit" class="text-red-500 hover:text-red-400">Delete</button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="4" class="text-center py-8 text-gray-400">No feeds configured. <a href="{{ url_for('add_feed') }}" class="text-indigo-400 hover:underline">Add one now!</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

ADD_FEED_TEMPLATE = """
<div class="bg-gray-800 p-6 rounded-xl shadow-lg">
    <h2 class="text-2xl font-semibold mb-4">Add a New Feed</h2>
    <form action="{{ url_for('add_feed') }}" method="post">
        <div class="mb-4">
            <label for="url" class="block text-gray-300 text-sm font-bold mb-2">RSS Feed URL</label>
            <input type="url" name="url" id="url" class="shadow appearance-none border border-gray-700 rounded-lg w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline focus:border-indigo-500" required>
        </div>
        <div class="mb-4">
            <label for="webhook_url" class="block text-gray-300 text-sm font-bold mb-2">Discord Webhook URL</label>
            <input type="url" name="webhook_url" id="webhook_url" class="shadow appearance-none border border-gray-700 rounded-lg w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline focus:border-indigo-500" required>
        </div>
        <div class="mb-6">
            <label for="update_interval" class="block text-gray-300 text-sm font-bold mb-2">Refresh Interval (seconds)</label>
            <input type="number" name="update_interval" id="update_interval" value="300" min="60" class="shadow appearance-none border border-gray-700 rounded-lg w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline focus:border-indigo-500" required>
        </div>
        <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition-colors duration-200">
            Add Feed
        </button>
    </form>
</div>
"""

EDIT_FEED_TEMPLATE = """
<div class="bg-gray-800 p-6 rounded-xl shadow-lg">
    <h2 class="text-2xl font-semibold mb-4">Edit Feed</h2>
    <form action="{{ url_for('edit_feed', feed_id=feed.id) }}" method="post">
        <div class="mb-4">
            <label for="url" class="block text-gray-300 text-sm font-bold mb-2">RSS Feed URL</label>
            <input type="url" name="url" id="url" value="{{ feed.url }}" class="shadow appearance-none border border-gray-700 rounded-lg w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline focus:border-indigo-500" required>
        </div>
        <div class="mb-4">
            <label for="webhook_url" class="block text-gray-300 text-sm font-bold mb-2">Discord Webhook URL</label>
            <input type="url" name="webhook_url" id="webhook_url" value="{{ feed.webhook_url }}" class="shadow appearance-none border border-gray-700 rounded-lg w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline focus:border-indigo-500" required>
        </div>
        <div class="mb-6">
            <label for="update_interval" class="block text-gray-300 text-sm font-bold mb-2">Refresh Interval (seconds)</label>
            <input type="number" name="update_interval" id="update_interval" value="{{ feed.update_interval }}" min="60" class="shadow appearance-none border border-gray-700 rounded-lg w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline focus:border-indigo-500" required>
        </div>
        <div class="flex items-center space-x-4">
            <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition-colors duration-200">
                Save Changes
            </button>
            <a href="{{ url_for('view_feeds') }}" class="text-gray-400 hover:text-white">Cancel</a>
        </div>
    </form>
</div>
"""

# This dictionary will act as a simple template loader.
TEMPLATES = {
    "layout": LAYOUT_TEMPLATE,
    "view_feeds": VIEW_FEEDS_TEMPLATE,
    "add_feed": ADD_FEED_TEMPLATE,
    "edit_feed": EDIT_FEED_TEMPLATE
}

# --- Configuration and State Management ---

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

def save_sent_articles(sent_articles):
    with open(SENT_ARTICLES_FILE, 'w') as f:
        yaml.dump(list(sent_articles), f)

def save_feed_state(feed_state):
     with open(FEED_STATE_FILE, 'w') as f:
        json.dump(feed_state, f, indent=4)

def initialize_files():
    """Ensure all necessary files exist before the app starts."""
    if not os.path.exists(CONFIG_FILE):
        save_config({"FEEDS": []})
        print(f"Created default {CONFIG_FILE}")
    if not os.path.exists(SENT_ARTICLES_FILE):
        save_sent_articles(set())
        print(f"Created default {SENT_ARTICLES_FILE}")
    if not os.path.exists(FEED_STATE_FILE):
        save_feed_state({})
        print(f"Created default {FEED_STATE_FILE}")

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def load_sent_articles():
    with open(SENT_ARTICLES_FILE, 'r') as f:
        content = f.read()
        if not content: return set()
        return set(yaml.safe_load(content) or [])

def load_feed_state():
    with open(FEED_STATE_FILE, 'r') as f:
        content = f.read()
        if not content: return {}
        return json.load(f)

# --- Initialize files on application startup ---
initialize_files()

# --- Flask Routes ---

@app.route('/')
def view_feeds():
    config = load_config()
    full_html = TEMPLATES["layout"].replace('{% block content %}{% endblock %}', TEMPLATES["view_feeds"])
    return render_template_string(full_html, config=config)

@app.route('/add', methods=['GET', 'POST'])
def add_feed():
    if request.method == 'POST':
        config = load_config()
        new_feed = {
            "id": str(uuid.uuid4()),
            "url": request.form['url'],
            "webhook_url": request.form['webhook_url'],
            "update_interval": int(request.form['update_interval'])
        }
        config['FEEDS'].append(new_feed)
        save_config(config)
        
        if scheduler_instance:
            print(f"Performing initial check for new feed: {new_feed['url']}")
            thread = threading.Thread(target=scheduler_instance.check_single_feed, args=(new_feed, True), daemon=True)
            thread.start()
            flash(f'Feed "{new_feed["url"]}" added! Performing initial check for the latest post...', 'success')
        else:
            flash(f'Feed "{new_feed["url"]}" added successfully! It will be checked on the next cycle.', 'success')

        return redirect(url_for('view_feeds'))
    
    full_html = TEMPLATES["layout"].replace('{% block content %}{% endblock %}', TEMPLATES["add_feed"])
    return render_template_string(full_html)

@app.route('/edit/<feed_id>', methods=['GET', 'POST'])
def edit_feed(feed_id):
    config = load_config()
    feed_to_edit = next((feed for feed in config['FEEDS'] if feed['id'] == feed_id), None)

    if feed_to_edit is None:
        flash('Feed not found.', 'error')
        return redirect(url_for('view_feeds'))

    if request.method == 'POST':
        # Find the index of the feed to update it in place
        for i, feed in enumerate(config['FEEDS']):
            if feed['id'] == feed_id:
                config['FEEDS'][i]['url'] = request.form['url']
                config['FEEDS'][i]['webhook_url'] = request.form['webhook_url']
                config['FEEDS'][i]['update_interval'] = int(request.form['update_interval'])
                break
        
        save_config(config)
        flash(f'Feed updated successfully!', 'success')
        return redirect(url_for('view_feeds'))

    # For GET request, render the edit form
    full_html = TEMPLATES["layout"].replace('{% block content %}{% endblock %}', TEMPLATES["edit_feed"])
    return render_template_string(full_html, feed=feed_to_edit)

@app.route('/delete/<feed_id>', methods=['POST'])
def delete_feed(feed_id):
    config = load_config()
    feed_to_delete = next((feed for feed in config['FEEDS'] if feed['id'] == feed_id), None)
    if feed_to_delete:
        config['FEEDS'] = [feed for feed in config['FEEDS'] if feed['id'] != feed_id]
        save_config(config)
        flash(f'Feed "{feed_to_delete["url"]}" deleted.', 'success')
    else:
        flash('Feed not found.', 'error')
    return redirect(url_for('view_feeds'))

# --- Feed Scheduler Class ---

class FeedScheduler:
    def __init__(self):
        self._loop = None
        self._is_running = False
        self._task = None

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        threading.Thread(target=self._run, daemon=True).start()
        print("Scheduler started.")

    def stop(self):
        if not self._is_running or not self._loop:
            return
        self._is_running = False
        self._loop.call_soon_threadsafe(self._loop.stop)
        print("Scheduler stopping...")

    def _run(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        self._loop = asyncio.get_event_loop()
        self._task = self._loop.create_task(self._schedule_loop())
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
        print("Scheduler stopped.")

    async def _schedule_loop(self):
        while self._is_running:
            print("Scheduler running check...")
            config = load_config()
            feed_state = load_feed_state()
            now = datetime.now(timezone.utc)

            for feed_config in config.get("FEEDS", []):
                feed_id = feed_config['id']
                last_checked_str = feed_state.get(feed_id)
                last_checked = datetime.fromisoformat(last_checked_str) if last_checked_str else None
                
                if not last_checked or (now - last_checked).total_seconds() >= feed_config['update_interval']:
                    print(f"Processing feed: {feed_config['url']}")
                    threading.Thread(target=self.check_single_feed, args=(feed_config, False), daemon=True).start()
                    feed_state[feed_id] = now.isoformat()
            
            save_feed_state(feed_state)
            await asyncio.sleep(60)

    def check_single_feed(self, feed_config, initial_check=False):
        """
        Fetches and posts new entries for a single feed via webhook.
        :param feed_config: The configuration dictionary for the feed.
        :param initial_check: If True, only the latest new item is posted. Otherwise, all new items are posted.
        """
        sent_articles = load_sent_articles()
        new_articles_found = False
        
        try:
            feed_data = feedparser.parse(feed_config['url'])
            if feed_data.bozo:
                print(f"Warning: Feed {feed_config['url']} may be malformed.")

            entries_to_process = feed_data.entries if initial_check else reversed(feed_data.entries)

            for entry in entries_to_process:
                article_id = entry.get('id', entry.link)
                if article_id not in sent_articles:
                    print(f"New article found: {entry.title}")
                    
                    message_content = f"**{feed_data.feed.title}**: {entry.title}\n{entry.link}"
                    payload = {"content": message_content}
                    
                    response = requests.post(feed_config['webhook_url'], json=payload)
                    if response.status_code >= 400:
                        print(f"Error sending to webhook for {feed_config['url']}: {response.status_code} {response.text}")
                    else:
                        new_articles_found = True
                        sent_articles.add(article_id)

                    if initial_check:
                        print("Initial check complete, breaking after first new post.")
                        break
        except Exception as e:
            print(f"Error processing feed {feed_config['url']}: {e}")

        if new_articles_found:
            save_sent_articles(sent_articles)

# --- Start Scheduler on App Load ---
# This ensures the scheduler runs under Gunicorn
scheduler_instance = FeedScheduler()
scheduler_instance.start()

# --- Main Execution (for direct run) ---
if __name__ == "__main__":
    print("Starting Flask web server on http://0.0.0.0:5000")
    print("Open this address in your browser to configure the bot.")
    app.run(host='0.0.0.0', port=5000)
