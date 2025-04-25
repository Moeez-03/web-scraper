import time
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
        
    def setup_driver(self):
        """Set up the Selenium WebDriver."""
        chrome_options = Options()
        # Run in headless mode - comment out if you want to see the browser
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
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
            time.sleep(2)  # Wait for the page to load
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
                    cookie_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                    )
                    cookie_button.click()
                    print("Accepted cookies")
                except TimeoutException:
                    print("No cookie popup found or it has timed out")
                    
            elif self.site == "allegro":
                # Handle cookie popup on Allegro
                try:
                    cookie_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-role='accept-consent']"))
                    )
                    cookie_button.click()
                    print("Accepted cookies")
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
                search_input.send_keys(search_phrase)
                
                # Click search button
                search_button = self.driver.find_element(By.CSS_SELECTOR, "button[data-testid='search-submit']")
                search_button.click()
                
            elif self.site == "allegro":
                # Find search input and submit
                search_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-role='search-input']"))
                )
                search_input.clear()
                search_input.send_keys(search_phrase)
                
                # Click search button
                search_button = self.driver.find_element(By.CSS_SELECTOR, "button[data-role='search-button']")
                search_button.click()
                
            print(f"Searched for: {search_phrase}")
            time.sleep(3)  # Wait for search results to load
            
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
                        next_button.click()
                        print("Navigating to next page")
                        time.sleep(3)  # Wait for the next page to load
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
                        next_button.click()
                        print("Navigating to next page")
                        time.sleep(3)  # Wait for the next page to load
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
            sns.barplot(x=location_price.index, y=location_price.values)
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
            
            # Create pie chart
            plt.pie(category_counts, labels=category_counts.index, autopct='%1.1f%%', startangle=90)
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
            
            # Create histogram
            sns.histplot(df_filtered['price_value'], bins=20, kde=True)
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
            
            # Create bar chart with count annotations
            ax = sns.barplot(x=region_comparison.index, y=region_comparison['mean'])
            
            # Add count annotations
            for i, count in enumerate(region_comparison['count']):
                ax.text(i, region_comparison['mean'][i] + 50, f"n={count}", ha='center')
            
            plt.title(f'Average Price Comparison: {region} vs Other Regions')
            plt.ylabel('Average Price (zł)')
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(charts_dir, 'region_price_comparison.png')
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart saved: {chart_path}")
            
        except Exception as e:
            print(f"Error creating region comparison chart: {e}")
    
    def _create_price_per_sqm_chart(self, df, charts_dir):
        """Create chart showing price per square meter distribution."""
        try:
            # Filter out rows with no square meter data or price data
            df_with_sqm = df[(df['square_meters'] > 0) & (df['price_value'] > 0)]
            
            if len(df_with_sqm) > 0:
                plt.figure(figsize=(10, 6))
                
                # Remove outliers for better visualization
                df_filtered = df_with_sqm[df_with_sqm['price_per_sqm'] < df_with_sqm['price_per_sqm'].quantile(0.95)]
                
                # Create histogram
                sns.histplot(df_filtered['price_per_sqm'], bins=20, kde=True)
                plt.title('Price per Square Meter Distribution (excluding top 5% outliers)')
                plt.xlabel('Price per Square Meter (zł/m²)')
                plt.ylabel('Number of Listings')
                plt.tight_layout()
                
                # Save chart
                chart_path = os.path.join(charts_dir, 'price_per_sqm_distribution.png')
                plt.savefig(chart_path)
                plt.close()
                print(f"Chart saved: {chart_path}")
                
                # Create scatter plot of price vs. square meters
                plt.figure(figsize=(10, 6))
                sns.scatterplot(data=df_filtered, x='square_meters', y='price_value')
                plt.title('Price vs. Square Meters')
                plt.xlabel('Square Meters (m²)')
                plt.ylabel('Price (zł)')
                plt.tight_layout()
                
                # Save chart
                chart_path = os.path.join(charts_dir, 'price_vs_sqm_scatter.png')
                plt.savefig(chart_path)
                plt.close()
                print(f"Chart saved: {chart_path}")
            else:
                print("Insufficient data for price per square meter charts")
            
        except Exception as e:
            print(f"Error creating price per square meter chart: {e}")
    
    def _create_highest_price_chart(self, df, charts_dir):
        """Create chart showing listings with highest prices."""
        try:
            plt.figure(figsize=(12, 8))
            
            # Get top 10 highest priced listings
            top_listings = df.nlargest(10, 'price_value')
            
            # Create bar chart with truncated titles
            truncated_titles = top_listings['title'].apply(lambda x: x[:30] + '...' if len(x) > 30 else x)
            ax = sns.barplot(x=top_listings['price_value'], y=truncated_titles)
            
            # Add price annotations
            for i, price in enumerate(top_listings['price_value']):
                ax.text(price + (top_listings['price_value'].max() * 0.01), i, f"{price:,.0f} zł", va='center')
            
            plt.title('Top 10 Highest Priced Listings')
            plt.xlabel('Price (zł)')
            plt.ylabel('Listing Title')
            plt.tight_layout()
            
            # Save chart
            chart_path = os.path.join(charts_dir, 'highest_price_listings.png')
            plt.savefig(chart_path)
            plt.close()
            print(f"Chart saved: {chart_path}")
            
        except Exception as e:
            print(f"Error creating highest price chart: {e}")
    
    def generate_report(self, search_phrase, region, report_format="txt"):
        """Generate a report with insights from the scraped data."""
        if not self.listings:
            print("No data available for generating report")
            return False
        
        try:
            # Create reports directory if it doesn't exist
            reports_dir = "reports"
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)
            
            # Convert listings to DataFrame for analysis
            df = pd.DataFrame(self.listings)
            
            # Generate report filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{search_phrase.replace(' ', '_')}_{timestamp}.{report_format}"
            report_path = os.path.join(reports_dir, filename)
            
            # Generate report content
            report_content = self._generate_report_content(df, search_phrase, region)
            
            # Save report in the specified format
            if report_format == "txt":
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
            elif report_format == "md":
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
            elif report_format == "html":
                # Fixed HTML template - avoiding problematic f-string with backslashes
                html_head = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Classified Ads Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2, h3 { color: #2c3e50; }
        table { border-collapse: collapse; width: 100%; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .chart-container { margin: 20px 0; }
    </style>
</head>
<body>
"""
                # Format the report content for HTML
                html_content = report_content.replace('\n', '<br>')
                html_content = html_content.replace('# ', '<h1>')
                html_content = html_content.replace('## ', '<h2>')
                html_content = html_content.replace('### ', '<h3>')
                html_content = html_content.replace('<h1>', '<h1>').replace('</h1>', '')
                html_content = html_content.replace('<h2>', '<h2>').replace('</h2>', '')
                html_content = html_content.replace('<h3>', '<h3>').replace('</h3>', '')
                
                html_foot = """
</body>
</html>
"""
                # Combine all HTML parts
                full_html = html_head + html_content + html_foot
                
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(full_html)
            else:
                print(f"Unsupported report format: {report_format}")
                return False
            
            print(f"Report saved: {report_path}")
            return True
            
        except Exception as e:
            print(f"Error generating report: {e}")
            return False
    
    def _generate_report_content(self, df, search_phrase, region):
        """Generate the content for the report."""
        # Calculate various metrics
        total_listings = len(df)
        region_count = self.count_listings_by_region(region)
        avg_price = df['price_value'].mean()
        median_price = df['price_value'].median()
        min_price = df['price_value'].min()
        max_price = df['price_value'].max()
        
        # Price per square meter metrics (for listings with this data)
        df_with_sqm = df[(df['square_meters'] > 0) & (df['price_value'] > 0)]
        
        if len(df_with_sqm) > 0:
            avg_sqm = df_with_sqm['square_meters'].mean()
            avg_price_per_sqm = df_with_sqm['price_per_sqm'].mean()
            median_price_per_sqm = df_with_sqm['price_per_sqm'].median()
            min_price_per_sqm = df_with_sqm['price_per_sqm'].min()
            max_price_per_sqm = df_with_sqm['price_per_sqm'].max()
        else:
            avg_sqm = 0
            avg_price_per_sqm = 0
            median_price_per_sqm = 0
            min_price_per_sqm = 0
            max_price_per_sqm = 0
        
        # Get top locations
        top_locations = df['location'].value_counts().head(5)
        
        # Get category distribution
        category_dist = df['category'].value_counts()
        
        # Format the report
        report = f"""# Classified Ads Analysis Report

## Overview
Search phrase: {search_phrase}
Target region: {region}
Total listings found: {total_listings}
Listings in target region: {region_count} ({(region_count/total_listings*100):.1f}% of total)

## Price Analysis
Average price: {avg_price:.2f} zł
Median price: {median_price:.2f} zł
Price range: {min_price:.2f} zł - {max_price:.2f} zł

## Square Meter Analysis
Listings with square meter data: {len(df_with_sqm)} ({(len(df_with_sqm)/total_listings*100):.1f}% of total)
Average square meters: {avg_sqm:.2f} m²
Average price per square meter: {avg_price_per_sqm:.2f} zł/m²
Median price per square meter: {median_price_per_sqm:.2f} zł/m²
Price per square meter range: {min_price_per_sqm:.2f} zł/m² - {max_price_per_sqm:.2f} zł/m²

## Top 5 Locations
"""
        
        for location, count in top_locations.items():
            report += f"- {location}: {count} listings ({(count/total_listings*100):.1f}%)\n"
        
        report += "\n## Category Distribution\n"
        for category, count in category_dist.items():
            report += f"- {category}: {count} listings ({(count/total_listings*100):.1f}%)\n"
        
        # Region-specific analysis
        if region_count > 0:
            region_pattern = re.compile(region, re.IGNORECASE)
            df['is_target_region'] = df['location'].apply(lambda x: bool(region_pattern.search(x)))
            region_df = df[df['is_target_region']]
            other_df = df[~df['is_target_region']]
            
            region_avg_price = region_df['price_value'].mean()
            other_avg_price = other_df['price_value'].mean()
            
            price_diff = region_avg_price - other_avg_price
            price_diff_pct = (price_diff / other_avg_price) * 100 if other_avg_price != 0 else 0
            
            # Calculate region-specific square meter metrics if data is available
            region_df_with_sqm = region_df[(region_df['square_meters'] > 0) & (region_df['price_value'] > 0)]
            
            if len(region_df_with_sqm) > 0:
                region_avg_sqm = region_df_with_sqm['square_meters'].mean()
                region_avg_price_per_sqm = region_df_with_sqm['price_per_sqm'].mean()
                
                # Compare with other regions
                other_df_with_sqm = other_df[(other_df['square_meters'] > 0) & (other_df['price_value'] > 0)]
                
                if len(other_df_with_sqm) > 0:
                    other_avg_price_per_sqm = other_df_with_sqm['price_per_sqm'].mean()
                    sqm_price_diff = region_avg_price_per_sqm - other_avg_price_per_sqm
                    sqm_price_diff_pct = (sqm_price_diff / other_avg_price_per_sqm) * 100 if other_avg_price_per_sqm != 0 else 0
                else:
                    other_avg_price_per_sqm = 0
                    sqm_price_diff = 0
                    sqm_price_diff_pct = 0
                
                report += f"""
## Region Analysis: {region}
Average price in {region}: {region_avg_price:.2f} zł
Average price in other regions: {other_avg_price:.2f} zł
Price difference: {price_diff:.2f} zł ({price_diff_pct:.1f}%)

### Square Meter Analysis for {region}
Average square meters in {region}: {region_avg_sqm:.2f} m²
Average price per square meter in {region}: {region_avg_price_per_sqm:.2f} zł/m²
Average price per square meter in other regions: {other_avg_price_per_sqm:.2f} zł/m²
Price per square meter difference: {sqm_price_diff:.2f} zł/m² ({sqm_price_diff_pct:.1f}%)
"""
            else:
                report += f"""
## Region Analysis: {region}
Average price in {region}: {region_avg_price:.2f} zł
Average price in other regions: {other_avg_price:.2f} zł
Price difference: {price_diff:.2f} zł ({price_diff_pct:.1f}%)

Note: No square meter data available for listings in {region}.
"""
            
            # Category distribution in the target region
            region_categories = region_df['category'].value_counts()
            report += f"\n### Category Distribution in {region}\n"
            for category, count in region_categories.items():
                report += f"- {category}: {count} listings ({(count/len(region_df)*100):.1f}%)\n"
        
        report += f"""
## Charts
Charts have been saved in the 'charts' directory:
- Average price by location: avg_price_by_location.png
- Category distribution: category_distribution.png
- Price distribution: price_distribution.png
- Price per square meter distribution: price_per_sqm_distribution.png
- Price vs. square meters scatter plot: price_vs_sqm_scatter.png
- Highest price listings: highest_price_listings.png
- Region comparison: region_price_comparison.png

## Report Generated
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        return report
    
    def count_listings_by_region(self, region):
        """Count listings from a specific region."""
        region_pattern = re.compile(region, re.IGNORECASE)
        count = sum(1 for listing in self.listings if region_pattern.search(listing['location']))
        return count
            
    def cleanup(self):
        """Close the browser and database connection, and perform cleanup."""
        if self.driver:
            self.driver.quit()
            print("Browser closed")
            
        if self.db_conn:
            self.db_conn.close()
            print("Database connection closed")
            
    def run_scraper(self, search_phrase, region, pages=3, generate_charts=True, generate_report=True, report_format="txt"):
        """Run the full scraping process."""
        try:
            self.setup_driver()
            self.setup_database()
            self.navigate_to_site()
            self.handle_popups()
            self.search_listings(search_phrase)
            
            # Scrape multiple pages
            page_count = 1
            while page_count <= pages:
                print(f"Scraping page {page_count}")
                self.scrape_page(search_phrase)
                
                if page_count < pages:
                    has_next = self.navigate_to_next_page()
                    if not has_next:
                        break
                page_count += 1
                
            # Count and report results
            region_count = self.count_listings_by_region(region)
            print(f"Found {region_count} listings containing \"{region}\"")
            
            # Save data to database
            self.save_to_database()
            
            # Save data to files
            self.save_to_file()
            
            # Generate charts if requested
            if generate_charts:
                self.generate_charts(search_phrase, region)
                
            # Generate report if requested
            if generate_report:
                self.generate_report(search_phrase, region, report_format)
            
        except Exception as e:
            print(f"Error running scraper: {e}")
        finally:
            self.cleanup()
            
def main():
    """Main function to run the scraper."""
    print("=" * 50)
    print("Enhanced Classified Ads Scraper")
    print("=" * 50)
    
    # Get user input
    site = input("Choose website (olx/allegro) [default: olx]: ").strip() or "olx"
    search_phrase = input("Enter search phrase: ").strip()
    region = input("Enter region to count: ").strip()
    
    try:
        pages = int(input("Enter number of pages to scrape [default: 3]: ").strip() or "3")
    except ValueError:
        print("Invalid number, using default (3)")
        pages = 3
    
    # Ask about visualization and reporting
    generate_charts = input("Generate data visualization charts? (y/n) [default: y]: ").strip().lower() != 'n'
    generate_report = input("Generate analysis report? (y/n) [default: y]: ").strip().lower() != 'n'
    
    report_format = "txt"
    if generate_report:
        format_choice = input("Choose report format (txt/md/html) [default: txt]: ").strip().lower()
        if format_choice in ["txt", "md", "html"]:
            report_format = format_choice
    
    # Initialize and run scraper
    scraper = ClassifiedScraper(site)
    scraper.run_scraper(search_phrase, region, pages, generate_charts, generate_report, report_format)

if __name__ == "__main__":
    main()