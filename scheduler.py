# scheduler.py
# This is a dedicated script to run the background feed checker.

import os
import asyncio
import feedparser
import yaml
import json
import threading
import requests
import time
from datetime import datetime, timezone

# --- Configuration & State Files ---
CONFIG_FILE = "config.json"
SENT_ARTICLES_FILE = "sent_articles.yaml"
FEED_STATE_FILE = "feed_state.json"

# --- Threading Lock ---
# This lock prevents race conditions when multiple threads access the sent_articles file.
file_lock = threading.Lock()

# --- Set a common User-Agent for all feedparser requests ---
feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0"

def initialize_files():
    """Ensure all necessary files exist before the app starts."""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"FEEDS": []}, f)
        print(f"Created default {CONFIG_FILE}")
    if not os.path.exists(SENT_ARTICLES_FILE):
        with open(SENT_ARTICLES_FILE, 'w') as f:
            yaml.dump([], f)
        print(f"Created default {SENT_ARTICLES_FILE}")
    if not os.path.exists(FEED_STATE_FILE):
        with open(FEED_STATE_FILE, 'w') as f:
            json.dump({}, f)
        print(f"Created default {FEED_STATE_FILE}")

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        content = f.read()
        if not content:
            return {"FEEDS": []}
        return json.loads(content)

def save_feed_state(feed_state):
     with open(FEED_STATE_FILE, 'w') as f:
        json.dump(feed_state, f, indent=4)

def load_feed_state():
    with open(FEED_STATE_FILE, 'r') as f:
        content = f.read()
        if not content:
            return {}
        return json.loads(content)

def post_if_new(article_id, message_content, webhook_url):
    """
    Atomically checks if an article is new and posts it if so.
    This function is thread-safe.
    """
    with file_lock:
        # 1. Read the current list of sent articles
        sent_articles = set()
        try:
            with open(SENT_ARTICLES_FILE, 'r') as f:
                content = f.read()
                if content:
                    sent_articles = set(yaml.safe_load(content) or [])
        except FileNotFoundError:
            pass # File will be created on write

        # 2. Check if the article is new
        if article_id not in sent_articles:
            print(f"New article found, posting: {message_content.splitlines()[0]}")
            
            # 3. Post to Discord
            payload = {"content": message_content}
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code < 400:
                # 4. If successful, add to the list and save
                sent_articles.add(article_id)
                with open(SENT_ARTICLES_FILE, 'w') as f:
                    yaml.dump(list(sent_articles), f)
                return True
            else:
                print(f"Error sending to webhook: {response.status_code} {response.text}")
                return False
        return False # Article was already sent

class FeedScheduler:
    def __init__(self):
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        """The main loop that checks feeds periodically."""
        print("Scheduler started.")
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
                    threading.Thread(target=self.check_single_feed, args=(feed_config,), daemon=True).start()
                    feed_state[feed_id] = now.isoformat()
            
            save_feed_state(feed_state)
            time.sleep(60) # Check every 60 seconds
        print("Scheduler stopped.")

    def check_single_feed(self, feed_config):
        """Fetches and posts new entries for a single feed via webhook."""
        try:
            feed_data = feedparser.parse(feed_config['url'])
            if feed_data.bozo:
                print(f"Warning: Feed {feed_config['url']} may be malformed.")

            for entry in reversed(feed_data.entries):
                article_id = entry.get('id', entry.link)
                message_content = f"**{feed_data.feed.title}**: {entry.title}\n{entry.link}"
                post_if_new(article_id, message_content, feed_config['webhook_url'])

        except Exception as e:
            print(f"Error processing feed {feed_config['url']}: {e}")

if __name__ == "__main__":
    initialize_files()
    scheduler = FeedScheduler()
    try:
        scheduler.run()
    except KeyboardInterrupt:
        scheduler.stop()
