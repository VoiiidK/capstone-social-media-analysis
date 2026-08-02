import pandas as pd
import os
from datetime import datetime, timedelta
from DrissionPage import ChromiumPage, ChromiumOptions
from time import sleep
import random

ACCOUNTS = [
    {
        "username": "",
        "password": "",
        "email": "",
        "email_pwd": ""
    }
]

USERS_CSV_PATH = "users.csv"
START_DATE = "2024-08-01"
END_DATE = "2025-11-13"
DATA_FOLDER = "tweets_data"

class TwitterScraper:
    def __init__(self):
        self.min_delay = 3
        self.max_delay = 4
        self.duplicate_cache = set()
        self.end_date = datetime.strptime(END_DATE, "%Y-%m-%d")
        self.start_date = datetime.strptime(START_DATE, "%Y-%m-%d")
        os.makedirs(DATA_FOLDER, exist_ok=True)
        
        # Setup browser
        co = ChromiumOptions()

        browser_paths = [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe']
        for path in browser_paths:
            if os.path.exists(path):
                co.set_browser_path(path)
                print(f"Browser path: {path}")
                break
        else:
            raise FileNotFoundError("Browser not found")
        
        co.headless(False)
        co.set_argument('--disable-blink-features=AutomationControlled')
        self.page = ChromiumPage(co)
        self.page.set.user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    async def login(self, account):
        print(f"Logging in: {account['username']}")
        self.page.get('https://twitter.com/login')
        
        # Wait
        self.page.ele('xpath://input[@name="text"]').input(account['username'])
        self.page.ele('xpath://span[contains(text(),"Next")]').click()
        sleep(random.uniform(1, 3))
        
        # Verification
        if "unusual login activity" in self.page.html:
            self.page.ele('xpath://input[@name="text"]').input(account['email'])
            self.page.ele('xpath://span[contains(text(),"Next")]').click()
            sleep(random.uniform(1, 3))
        
        # Password
        self.page.ele('xpath://input[@name="password"]').input(account['password'])
        self.page.ele('xpath://span[contains(text(),"Log in")]').click()
        sleep(5)
        
        # Check log in
        if "home" in self.page.url:
            print(f"Log in successed: {account['username']}")
            return True
        print(f"Log in failed: {account['username']}")
        return False

    def get_last_date(self, username):
        """Get last scrape date"""
        csv_path = f"{DATA_FOLDER}/{username}.csv"
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                last_date = pd.to_datetime(df['created_at']).max()
                print(f"History Found: {last_date.date()}")
                return min(
                    last_date + timedelta(days=1),
                    datetime.now()
                )
            except Exception as e:
                print(f"Failed to find history: {str(e)}")
        return min(
            datetime.now(),
            self.end_date
        )

    def is_duplicate(self, tweet_id, content):
        key = f"{tweet_id}_{hash(content[:100])}"
        if key in self.duplicate_cache:
            return True
        self.duplicate_cache.add(key)
        return False

    def random_delay(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        print(f"Wait for {delay:.1f} s...")
        sleep(delay)

    def scrape_user_tweets(self, username):
        try:
            last_date = self.get_last_date(username)
            print(f"\n▶ Start scrape @{username} (From: {last_date.date()} to {self.start_date.date()})")
            
            # Access account page
            url = f"https://twitter.com/{username}"
            self.page.get(url)
            sleep(5)
            
            # Rolling
            last_tweet_count = 0
            same_count = 0
            max_same_count = 3
            
            while True:
                # Scrape elements
                tweets = self.page.eles('xpath://article[@data-testid="tweet"]')
                current_tweet_count = len(tweets)
                
                # No new posts
                if current_tweet_count == last_tweet_count:
                    same_count += 1
                    if same_count >= max_same_count:
                        print("All posts loaded")
                        break
                else:
                    same_count = 0
                    last_tweet_count = current_tweet_count
                
                for tweet in tweets:
                    try:
                        # Extract post
                        tweet_id = tweet.attr('data-item-id')
                        content_element = tweet.ele('xpath:.//div[@data-testid="tweetText"]', timeout=2)
                        content = content_element.text if content_element else "No content"
                        date_element = tweet.ele('xpath:.//time', timeout=2)
                        if not date_element:
                            continue
                        date_str = date_element.attr('datetime')
                        tweet_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                        
                        # Date check
                        if tweet_date < self.start_date:
                            print(f"Reach date limit {self.start_date.date()}，stopping")
                            return
                        if tweet_date > last_date:
                            continue

                        if self.is_duplicate(tweet_id, content):
                            continue
                        
                        # Scrape interaction data
                        def get_interaction(element, testid):
                            try:
                                return element.ele(f'xpath:.//div[@data-testid="{testid}"]', timeout=1).text or "0"
                            except:
                                return "0"
                        
                        likes = get_interaction(tweet, 'like')
                        retweets = get_interaction(tweet, 'retweet')
                        replies = get_interaction(tweet, 'reply')
                        
                        # Save
                        df = pd.DataFrame([{
                            "content": content,
                            "created_at": tweet_date,
                            "likes": int(likes.replace(',', '')) if likes else 0,
                            "retweets": int(retweets.replace(',', '')) if retweets else 0,
                            "replies": int(replies.replace(',', '')) if replies else 0
                        }])
                        
                        print(f"[{tweet_date.strftime('%Y-%m-%d')}] {content[:50]}...")
                        
                        csv_path = f"{DATA_FOLDER}/{username}.csv"
                        df.to_csv(
                            csv_path,
                            mode='a',
                            header=not os.path.exists(csv_path),
                            index=False,
                            encoding='utf-8-sig'
                        )
                        
                    except Exception as e:
                        print(f"Error while scraping interaction: {str(e)}")
                        continue
                
                # Rolling
                self.page.scroll.down(1500)
                sleep(random.uniform(2, 5))

                self.random_delay()
                
        except Exception as e:
            print(f"Error: {str(e)}")
            sleep(60)

def main():
    print("=== Twitter Scraper Start ===")
    scraper = TwitterScraper()
    
    # Log in
    if not ACCOUNTS:
        print("No account, stopping...")
        return
    
    if not scraper.login(ACCOUNTS[0]):
        print("No available account, stopping...")
        return
    
    try:
        with open(USERS_CSV_PATH, 'r', encoding='utf-8') as f:
            users = [u.strip() for line in f for u in line.split(",") if u.strip()]
        
        print(f"\n Account to scrape: {', '.join(users)}")
        for user in users:
            scraper.scrape_user_tweets(user)
            sleep(random.randint(30, 60))

    except FileNotFoundError:
        print(f" Error: No account list {USERS_CSV_PATH}")
    except Exception as e:
        print(f"Error: {str(e)}")

    print("\n=== Finish scraping ===")
    scraper.page.quit()

if __name__ == "__main__":
    main()
