import time
import random
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import re
import os
import numpy as np
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import matplotlib
import sqlite3
matplotlib.use('Agg')  # Use non-interactive backend

class ClassifiedScraper:
    def __init__(self, site="olx"):
        """Initialize the scraper with selected site."""
        self.site = site.lower()
        self.driver = None
        self.listings = []
        self.db_conn = None
        
        # User agent rotation list
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
        ]
        
    def setup_driver(self):
        """Set up the Selenium WebDriver with rotating user agent."""
        chrome_options = Options()
        # Run in headless mode - comment out if you want to see the browser
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        
        # Select a random user agent
        user_agent = random.choice(self.user_agents)
        chrome_options.add_argument(f"user-agent={user_agent}")
        
        # Additional options to avoid detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Modify navigator properties to avoid detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print(f"WebDriver setup with user agent: {user_agent}")
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            exit(1)
    
    def setup_database(self):
        """Set up SQLite database for storing listings."""
        try:
            # Connect to SQLite database (will be created if it doesn't exist)
            self.db_conn = sqlite3.connect('listings.db')
            cursor = self.db_conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                location TEXT,
                price TEXT,
                price_value REAL,
                url TEXT,
                date_posted TEXT,
                category TEXT,
                square_meters REAL,
                price_per_sqm REAL,
                search_phrase TEXT,
                scraped_date TEXT
            )
            ''')
            
            self.db_conn.commit()
            print("Database setup complete")
            
        except Exception as e:
            print(f"Error setting up database: {e}")
            if self.db_conn:
                self.db_conn.close()
    
    def random_wait(self, min_seconds=2, max_seconds=5):
        """Wait for a random amount of time between requests to appear more human-like."""
        wait_time = random.uniform(min_seconds, max_seconds)
        time.sleep(wait_time)
        return wait_time
                
    def navigate_to_site(self):
        """Navigate to the classified ads website."""
        try:
            if self.site == "olx":
                self.driver.get("https://www.olx.pl/")
            elif self.site == "allegro":
                self.driver.get("https://allegro.pl/")
            else:
                print(f"Site {self.site} not supported. Using OLX as default.")
                self.driver.get("https://www.olx.pl/")
                self.site = "olx"
                
            print(f"Navigated to {self.site}")
            
            # Dynamic wait for page to load completely
            wait_time = self.random_wait(3, 6)
            print(f"Waiting {wait_time:.2f} seconds for page to fully load")
        except Exception as e:
            print(f"Error navigating to site: {e}")
            self.cleanup()
            exit(1)
    
    def handle_popups(self):
        """Handle common popups like cookie notices."""
        try:
            if self.site == "olx":
                # Handle cookie popup on OLX
                try:
                    cookie_button = WebDriverWait(self.driver, 8).until(
                        EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                    )
                    cookie_button.click()
                    print("Accepted cookies")
                    self.random_wait(1, 2)  # Short wait after clicking
                except TimeoutException:
                    print("No cookie popup found or it has timed out")
                    
            elif self.site == "allegro":
                # Handle cookie popup on Allegro
                try:
                    cookie_button = WebDriverWait(self.driver, 8).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-role='accept-consent']"))
                    )
                    cookie_button.click()
                    print("Accepted cookies")
                    self.random_wait(1, 2)  # Short wait after clicking
                except TimeoutException:
                    print("No cookie popup found or it has timed out")
                    
        except Exception as e:
            print(f"Error handling popups: {e}")
            
    def search_listings(self, search_phrase):
        """Search for listings using the given search phrase."""
        try:
            if self.site == "olx":
                # Find search input and submit
                search_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input']"))
                )
                search_input.clear()
                
                # Type search phrase with random delays between characters
                for char in search_phrase:
                    search_input.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.2))  # Random delay between keystrokes
                
                # Short pause before clicking search button to mimic human behavior
                self.random_wait(0.5, 1.5)
                
                # Click search button
                search_button = self.driver.find_element(By.CSS_SELECTOR, "button[data-testid='search-submit']")
                search_button.click()
                
            elif self.site == "allegro":
                # Find search input and submit
                search_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-role='search-input']"))
                )
                search_input.clear()
                
                # Type search phrase with random delays between characters
                for char in search_phrase:
                    search_input.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.2))  # Random delay between keystrokes
                
                # Short pause before clicking search button
                self.random_wait(0.5, 1.5)
                
                # Click search button
                search_button = self.driver.find_element(By.CSS_SELECTOR, "button[data-role='search-button']")
                search_button.click()
                
            print(f"Searched for: {search_phrase}")
            
            # Wait for search results to load with dynamic timing
            wait_time = self.random_wait(4, 7)
            print(f"Waiting {wait_time:.2f} seconds for search results to load")
            
            # Check if page has loaded properly
            try:
                if self.site == "olx":
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cy='l-card']"))
                    )
                elif self.site == "allegro":
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-role='offer']"))
                    )
                print("Search results page loaded successfully")
            except TimeoutException:
                print("Warning: Could not confirm search results loaded. Continuing anyway...")
            
        except Exception as e:
            print(f"Error searching listings: {e}")
            
    def scrape_page(self, search_phrase):
        """Scrape listing data from the current page."""
        try:
            # Get page source for BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            if self.site == "olx":
                # Find all listing items on OLX
                listing_items = soup.select('div[data-cy="l-card"]')
                
                for item in listing_items:
                    try:
                        # Extract title
                        title_element = item.select_one('h6')
                        title = title_element.text.strip() if title_element else "No Title"
                        
                        # Extract location and date
                        location_element = item.select_one('p[data-testid="location-date"]')
                        location_text = location_element.text.strip() if location_element else "No Location"
                        
                        # Extract location (before the date)
                        location = location_text.split(' - ')[0] if ' - ' in location_text else location_text
                        
                        # Extract date posted (after the location)
                        date_posted = location_text.split(' - ')[1] if ' - ' in location_text else "No Date"
                        
                        # Extract price
                        price_element = item.select_one('p[data-testid="ad-price"]')
                        price_text = price_element.text.strip() if price_element else "0 zł"
                        
                        # Extract numeric price for analysis
                        price_value = self._extract_price(price_text)
                        
                        # Extract URL
                        url_element = item.select_one('a')
                        url = url_element['href'] if url_element and 'href' in url_element.attrs else "No URL"
                        if url.startswith('/'):
                            url = f"https://www.olx.pl{url}"
                        
                        # Extract square meters from title
                        square_meters = self._extract_square_meters(title)
                        
                        # Calculate price per square meter if both values are available
                        price_per_sqm = price_value / square_meters if price_value > 0 and square_meters > 0 else 0
                        
                        # Extract category if possible
                        category = self._extract_category(title)
                        
                        # Add data to listings
                        self.listings.append({
                            'title': title,
                            'location': location,
                            'price': price_text,
                            'price_value': price_value,
                            'url': url,
                            'date_posted': date_posted,
                            'category': category,
                            'square_meters': square_meters,
                            'price_per_sqm': price_per_sqm,
                            'search_phrase': search_phrase,
                            'scraped_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                    except Exception as e:
                        print(f"Error scraping individual listing: {e}")
                        continue
                        
            elif self.site == "allegro":
                # Find all listing items on Allegro
                listing_items = soup.select('article[data-role="offer"]')
                
                for item in listing_items:
                    try:
                        # Extract title
                        title_element = item.select_one('h2')
                        title = title_element.text.strip() if title_element else "No Title"
                        
                        # Extract location (if available)
                        location_element = item.select_one('div[data-role="seller-info"] span')
                        location = location_element.text.strip() if location_element else "No Location"
                        
                        # Extract date posted (not always available on Allegro search page)
                        date_posted = "Not available"  # Default value
                        
                        # Extract price
                        price_element = item.select_one('div[data-role="price"]')
                        price_text = price_element.text.strip() if price_element else "0 zł"
                        
                        # Extract numeric price for analysis
                        price_value = self._extract_price(price_text)
                        
                        # Extract URL
                        url_element = item.select_one('a')
                        url = url_element['href'] if url_element and 'href' in url_element.attrs else "No URL"
                        
                        # Extract square meters from title
                        square_meters = self._extract_square_meters(title)
                        
                        # Calculate price per square meter if both values are available
                        price_per_sqm = price_value / square_meters if price_value > 0 and square_meters > 0 else 0
                        
                        # Extract category if possible
                        category = self._extract_category(title)
                        
                        # Add data to listings
                        self.listings.append({
                            'title': title,
                            'location': location,
                            'price': price_text,
                            'price_value': price_value,
                            'url': url,
                            'date_posted': date_posted,
                            'category': category,
                            'square_meters': square_meters,
                            'price_per_sqm': price_per_sqm,
                            'search_phrase': search_phrase,
                            'scraped_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                    except Exception as e:
                        print(f"Error scraping individual listing: {e}")
                        continue
                        
            print(f"Scraped {len(self.listings)} listings so far")
            
        except Exception as e:
            print(f"Error scraping page: {e}")
    
    def _extract_price(self, price_text):
        """Extract numeric price value from price text."""
        try:
            # Remove currency symbol and spaces, keep only digits and decimal point
            price_digits = re.sub(r'[^\d.]', '', price_text.replace(',', '.'))
            if price_digits:
                return float(price_digits)
            return 0.0
        except:
            return 0.0
    
    def _extract_square_meters(self, text):
        """Extract square meters from text."""
        try:
            # Look for common patterns like "50 m2", "50m2", "50 mkw", etc.
            patterns = [
                r'(\d+[\.,]?\d*)\s*m2',
                r'(\d+[\.,]?\d*)\s*mkw',
                r'(\d+[\.,]?\d*)\s*m²',
                r'(\d+[\.,]?\d*)\s*metr[óy]w'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Replace comma with dot and convert to float
                    return float(match.group(1).replace(',', '.'))
            
            return 0.0
        except:
            return 0.0
    
    def _extract_category(self, title):
        """Try to extract a category from the title."""
        # This is a simple implementation - you might want to improve this with
        # more sophisticated categorization based on your specific needs
        title_lower = title.lower()
        
        categories = {
            'electronics': ['laptop', 'komputer', 'telefon', 'smartfon', 'tablet', 'tv', 'telewizor', 'elektronika'],
            'vehicles': ['samochód', 'auto', 'samochod', 'pojazd', 'motocykl', 'skuter', 'rower'],
            'real estate': ['mieszkanie', 'dom', 'działka', 'dzialka', 'nieruchomość', 'nieruchomosc'],
            'jobs': ['praca', 'etat', 'zatrudnienie', 'zatrudnię', 'zatrudnie', 'job'],
            'services': ['usługa', 'usluga', 'usługi', 'uslugi', 'serwis'],
            'fashion': ['ubranie', 'odzież', 'odziez', 'buty', 'kurtka', 'spodnie', 'sukienka'],
            'furniture': ['meble', 'stół', 'stol', 'krzesło', 'krzeslo', 'szafa', 'łóżko', 'lozko', 'sofa'],
            'other': []
        }
        
        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        
        return 'other'
            
    def navigate_to_next_page(self):
        """Navigate to the next page of results if available."""
        try:
            if self.site == "olx":
                # Look for next page button on OLX
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, 'a[data-testid="pagination-forward"]')
                    if next_button:
                        # Random delay before clicking next page
                        self.random_wait(1, 3)
                        next_button.click()
                        print("Navigating to next page")
                        
                        # Wait for the next page to load with dynamic timing
                        wait_time = self.random_wait(4, 7)
                        print(f"Waiting {wait_time:.2f} seconds for next page to load")
                        return True
                    else:
                        print("No more pages")
                        return False
                except NoSuchElementException:
                    print("No more pages")
                    return False
                    
            elif self.site == "allegro":
                # Look for next page button on Allegro
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, 'a[data-role="next-page"]')
                    if next_button:
                        # Random delay before clicking next page
                        self.random_wait(1, 3)
                        next_button.click()
                        print("Navigating to next page")
                        
                        # Wait for the next page to load with dynamic timing
                        wait_time = self.random_wait(4, 7)
                        print(f"Waiting {wait_time:.2f} seconds for next page to load")
                        return True
                    else:
                        print("No more pages")
                        return False
                except NoSuchElementException:
                    print("No more pages")
                    return False
                    
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            return False
    
    def save_to_database(self):
        """Save the scraped data to SQLite database."""
        try:
            if not self.listings:
                print("No data to save to database")
                return False
                
            if not self.db_conn:
                print("Database connection not established")
                return False
                
            cursor = self.db_conn.cursor()
            
            # Insert each listing into the database
            for listing in self.listings:
                cursor.execute('''
                INSERT INTO listings (
                    title, location, price, price_value, url, date_posted, 
                    category, square_meters, price_per_sqm, search_phrase, scraped_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    listing['title'], listing['location'], listing['price'], 
                    listing['price_value'], listing['url'], listing['date_posted'],
                    listing['category'], listing['square_meters'], listing['price_per_sqm'],
                    listing['search_phrase'], listing['scraped_date']
                ))
                
            self.db_conn.commit()
            print(f"Data saved to database (listings.db)")
            return True
            
        except Exception as e:
            print(f"Error saving data to database: {e}")
            return False
            
    def save_to_file(self, filename="ogloszenia.csv", excel_filename="ogloszenia.xlsx"):
        """Save the scraped data to CSV and Excel files."""
        try:
            if not self.listings:
                print("No data to save")
                return False
                
            # Create DataFrame
            df = pd.DataFrame(self.listings)
            
            # Save to CSV
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"Data saved to {filename}")
            
            # Save to Excel with additional summary statistics
            with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Listings', index=False)
                
                # Summary statistics sheet
                summary_data = {
                    'Metric': [
                        'Total Listings', 
                        'Average Price', 
                        'Median Price',
                        'Highest Price',
                        'Lowest Price',
                        'Average Square Meters',
                        'Average Price per Sqm',
                        'Median Price per Sqm',
                        'Highest Price per Sqm'
                    ],
                    'Value': [
                        len(df),
                        df['price_value'].mean(),
                        df['price_value'].median(),
                        df['price_value'].max(),
                        df['price_value'].min(),
                        df[df['square_meters'] > 0]['square_meters'].mean(),
                        df[df['price_per_sqm'] > 0]['price_per_sqm'].mean(),
                        df[df['price_per_sqm'] > 0]['price_per_sqm'].median(),
                        df[df['price_per_sqm'] > 0]['price_per_sqm'].max()
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
            print(f"Data with summary statistics saved to {excel_filename}")
            return True
            
        except Exception as e:
            print(f"Error saving data to file: {e}")
            return False
    
    def generate_charts(self, search_phrase, region):
        """Generate charts based on scraped data."""
        if not self.listings:
            print("No data available for generating charts")
            return False
        
        try:
            # Convert listings to DataFrame for analysis
            df = pd.DataFrame(self.listings)
            
            # Create charts directory if it doesn't exist
            charts_dir = "charts"
            if not os.path.exists(charts_dir):
                os.makedirs(charts_dir)
            
            # 1. Average price by location
            self._create_price_by_location_chart(df, charts_dir)
            
            # 2. Listings count by category
            self._create_category_distribution_chart(df, charts_dir)
            
            # 3. Price distribution histogram
            self._create_price_distribution_chart(df, charts_dir)
            
            # 4. Region comparison chart if region is specified
            if region:
                self._create_region_comparison_chart(df, region, charts_dir)
            
            # 5. Price per square meter chart
            self._create_price_per_sqm_chart(df, charts_dir)
            
            # 6. Highest price listings
            self._create_highest_price_chart(df, charts_dir)
            
            # 7. Date distribution chart (new)
            self._create_date_distribution_chart(df, charts_dir)
            
            return True
            
        except Exception as e:
            print(f"Error generating charts: {e}")
            return False
    
    def _create_price_by_location_chart(self, df, charts_dir):
        """Create chart showing average price by location."""
        try:
            plt.figure(figsize=(12, 8))
            
            # Group by location and calculate mean price
            location_price = df.groupby('location')['price_value'].mean().sort_values(ascending=False).head(10)
            
            # Create bar chart
            ax = sns.barplot(x=location_price.index, y=location_price.values)
            
            # Add value labels on top of bars
            for i, v in enumerate(location_price.values):
                ax.text(i, v + (location_price.max() * 0.02), f"{v:.0f}", ha='center')
            
            plt.title('Average Price by Top 10 Locations')
            plt.xlabel('Location')
            plt.ylabel('Average Price (zł)')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(charts_dir, 'avg_price_by_location.png')
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart saved: {chart_path}")
            
        except Exception as e:
            print(f"Error creating location price chart: {e}")
    
    def _create_category_distribution_chart(self, df, charts_dir):
        """Create chart showing distribution of listings by category."""
        try:
            plt.figure(figsize=(10, 6))
            
            # Count listings per category
            category_counts = df['category'].value_counts()
            
            # Create pie chart with percentages
            wedges, texts, autotexts = plt.pie(
                category_counts, 
                labels=category_counts.index, 
                autopct='%1.1f%%', 
                startangle=90,
                shadow=True,
                explode=[0.05] * len(category_counts)  # Slightly explode all slices
            )
            
            # Style the percentage text
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            plt.title('Distribution of Listings by Category')
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(charts_dir, 'category_distribution.png')
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart saved: {chart_path}")
            
        except Exception as e:
            print(f"Error creating category distribution chart: {e}")
    
    def _create_price_distribution_chart(self, df, charts_dir):
        """Create histogram showing price distribution."""
        try:
            plt.figure(figsize=(10, 6))
            
            # Remove outliers for better visualization (optional)
            df_filtered = df[df['price_value'] < df['price_value'].quantile(0.95)]
            
            # Create histogram with KDE
            sns.histplot(df_filtered['price_value'], bins=20, kde=True, color='skyblue')
            
            # Add vertical line for mean and median
            mean_price = df_filtered['price_value'].mean()
            median_price = df_filtered['price_value'].median()
            
            plt.axvline(mean_price, color='red', linestyle='--', label=f'Mean: {mean_price:.0f} zł')
            plt.axvline(median_price, color='green', linestyle='-', label=f'Median: {median_price:.0f} zł')
            
            plt.legend()
            plt.title('Price Distribution (excluding top 5% outliers)')
            plt.xlabel('Price (zł)')
            plt.ylabel('Number of Listings')
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(charts_dir, 'price_distribution.png')
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart saved: {chart_path}")
            
        except Exception as e:
            print(f"Error creating price distribution chart: {e}")
    
    def _create_region_comparison_chart(self, df, region, charts_dir):
        """Create chart comparing prices in specified region vs other regions."""
        try:
            plt.figure(figsize=(8, 6))
            
            # Create a new column indicating if the listing is from the specified region
            region_pattern = re.compile(region, re.IGNORECASE)
            df['is_target_region'] = df['location'].apply(lambda x: bool(region_pattern.search(x)))
            
            # Group by region indicator and calculate mean price
            region_comparison = df.groupby('is_target_region')['price_value'].agg(['mean', 'count'])
            
            # Rename index for clarity
            region_comparison.index = [f"Other Regions", f"{region}"]
            
            # Create bar chart
            ax = sns.barplot(x=region_comparison.index, y=region_comparison['mean'])
            
            # Add value labels on top of bars
            for i, v in enumerate(region_comparison['mean']):
                ax.text(i, v + (region_comparison['mean'].max() * 0.02), 
                        f"{v:.0f} zł\n({region_comparison['count'][i]} listings)", ha='center')
            
            plt.title(f'Average Price: {region} vs Other Regions')
            plt.ylabel('Average Price (zł)')
            plt.ylim(0, region_comparison['mean'].max() * 1.2)  # Add some headroom for labels
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(charts_dir, 'region_comparison.png')
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart saved: {chart_path}")
            
        except Exception as e:
            print(f"Error creating region comparison chart: {e}")
    
    def _create_price_per_sqm_chart(self, df, charts_dir):
        """Create chart showing price per square meter."""
        try:
            plt.figure(figsize=(10, 6))
            
            # Filter out entries with zero or missing square meters and price
            valid_data = df[(df['square_meters'] > 0) & (df['price_value'] > 0)]
            
            if len(valid_data) == 0:
                print("No valid square meter data for chart")
                return
            
            # Remove outliers for better visualization
            filtered_data = valid_data[valid_data['price_per_sqm'] < valid_data['price_per_sqm'].quantile(0.95)]
            
            # Create scatter plot with regression line
            ax = sns.regplot(
                x='square_meters', 
                y='price_value', 
                data=filtered_data, 
                scatter_kws={'alpha':0.5},
                line_kws={'color':'red'}
            )
            
            plt.title('Price vs Size (m²)')
            plt.xlabel('Size (m²)')
            plt.ylabel('Price (zł)')
            
            # Add annotation with average price per sqm
            avg_price_per_sqm = filtered_data['price_per_sqm'].mean()
            plt.annotate(
                f'Avg. Price/m²: {avg_price_per_sqm:.0f} zł',
                xy=(0.95, 0.05),
                xycoords='axes fraction',
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                ha='right',
                fontsize=10
            )
            
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(charts_dir, 'price_per_sqm.png')
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart saved: {chart_path}")
            
        except Exception as e:
            print(f"Error creating price per square meter chart: {e}")
    
    def _create_highest_price_chart(self, df, charts_dir):
        """Create chart showing highest priced listings."""
        try:
            plt.figure(figsize=(14, 8))
            
            # Get top 10 most expensive listings
            top_listings = df.sort_values(by='price_value', ascending=False).head(10)
            
            # Create horizontal bar chart
            ax = sns.barplot(y=top_listings['title'].str[:50] + '...', x=top_listings['price_value'])
            
            # Add value labels
            for i, v in enumerate(top_listings['price_value']):
                ax.text(v + (top_listings['price_value'].max() * 0.02), i, f"{v:,.0f} zł", va='center')
            
            plt.title('Top 10 Most Expensive Listings')
            plt.xlabel('Price (zł)')
            plt.ylabel('Title')
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(charts_dir, 'highest_prices.png')
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart saved: {chart_path}")
            
        except Exception as e:
            print(f"Error creating highest price chart: {e}")
    
    def _create_date_distribution_chart(self, df, charts_dir):
        """Create chart showing distribution of listings by date posted."""
        try:
            plt.figure(figsize=(12, 6))
            
            # Extract clean date information if available
            date_counts = df['date_posted'].value_counts().sort_index()
            
            # Filter out non-date entries (like "No Date")
            valid_dates = [date for date in date_counts.index if date != "No Date" and date != "Not available"]
            if not valid_dates:
                print("No valid date information for chart")
                return
                
            # Create date count chart
            date_subset = date_counts[valid_dates]
            ax = sns.barplot(x=date_subset.index, y=date_subset.values)
            
            # Add counts on top of bars
            for i, v in enumerate(date_subset.values):
                ax.text(i, v + 0.5, str(v), ha='center')
            
            plt.title('Listings by Date Posted')
            plt.xlabel('Date Posted')
            plt.ylabel('Number of Listings')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(charts_dir, 'date_distribution.png')
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart saved: {chart_path}")
            
        except Exception as e:
            print(f"Error creating date distribution chart: {e}")
    
    def run_scraper(self, search_phrases, max_pages=3, region=None):
        """Run the full scraper pipeline for multiple search phrases."""
        try:
            # Setup initial components
            self.setup_driver()
            self.setup_database()
            self.navigate_to_site()
            self.handle_popups()
            
            # Process each search phrase
            for phrase in search_phrases:
                print(f"\n{'='*50}")
                print(f"Processing search phrase: {phrase}")
                print(f"{'='*50}")
                
                # Clear previous listings
                self.listings = []
                
                # Search for this phrase
                self.search_listings(phrase)
                
                # Scrape first page
                self.scrape_page(phrase)
                
                # Navigate through additional pages
                page_count = 1
                while page_count < max_pages:
                    if not self.navigate_to_next_page():
                        break  # No more pages
                    self.scrape_page(phrase)
                    page_count += 1
                
                # Save data to database
                self.save_to_database()
                
                # Save data to files
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{phrase.replace(' ', '_')}_{timestamp}.csv"
                excel_filename = f"{phrase.replace(' ', '_')}_{timestamp}.xlsx"
                self.save_to_file(filename, excel_filename)
                
                # Generate charts
                self.generate_charts(phrase, region)
                
                # Random wait before next search phrase
                wait_time = self.random_wait(5, 10)
                print(f"Waiting {wait_time:.2f} seconds before next search")
            
            print("\nScraping completed successfully!")
            
        except Exception as e:
            print(f"Error in scraper run: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                print("WebDriver closed")
                
            if self.db_conn:
                self.db_conn.close()
                print("Database connection closed")
                
        except Exception as e:
            print(f"Error in cleanup: {e}")


def main():
    """Main function to run the scraper with interactive user input."""
    print("="*50)
    print("Welcome to ClassifiedScraper!")
    print("="*50)
    
    # Ask for site to scrape
    print("\nWhich site would you like to scrape?")
    print("1. OLX")
    print("2. Allegro")
    site_choice = input("Enter your choice (1/2): ").strip()
    
    site = "olx"  # Default
    if site_choice == "2":
        site = "allegro"
    
    # Ask for search phrases
    print("\nWhat would you like to search for?")
    print("You can enter multiple search phrases separated by commas")
    search_input = input("Enter search phrase(s): ").strip()
    search_phrases = [phrase.strip() for phrase in search_input.split(',')]
    
    # Ask for number of pages
    print("\nHow many pages should be scraped for each search phrase?")
    pages_input = input("Enter number of pages (default is 3): ").strip()
    max_pages = 3  # Default
    if pages_input.isdigit() and int(pages_input) > 0:
        max_pages = int(pages_input)
    
    # Ask for region
    print("\nWould you like to do a region-specific analysis?")
    region_choice = input("Enter region name (or leave empty for no region analysis): ").strip()
    region = None if not region_choice else region_choice
    
    # Confirm choices before starting
    print("\n" + "="*50)
    print("Scraping Configuration:")
    print(f"Site: {site}")
    print(f"Search phrases: {search_phrases}")
    print(f"Max pages per search: {max_pages}")
    print(f"Region analysis: {'Yes - ' + region if region else 'No'}")
    print("="*50)
    
    confirm = input("\nStart scraping with these settings? (y/n): ").strip().lower()
    if confirm == 'y' or confirm == 'yes':
        # Create and run scraper
        scraper = ClassifiedScraper(site=site)
        scraper.run_scraper(search_phrases, max_pages=max_pages, region=region)
    else:
        print("Scraping cancelled. Please run the program again to start over.")


if __name__ == "__main__":
    main()