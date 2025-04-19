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
matplotlib.use('Agg')  # Use non-interactive backend

class ClassifiedScraper:
    def __init__(self, site="olx"):
        """Initialize the scraper with selected site."""
        self.site = site.lower()
        self.driver = None
        self.listings = []
        
    def setup_driver(self):
        """Set up the Selenium WebDriver."""
        chrome_options = Options()
        # Run in headless mode - comment out if you want to see the browser
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            exit(1)
            
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
            
    def scrape_page(self):
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
                        
                        # Extract location
                        location_element = item.select_one('p[data-testid="location-date"]')
                        location_text = location_element.text.strip() if location_element else "No Location"
                        # Extract just the location part (before the date)
                        location = location_text.split(' - ')[0] if ' - ' in location_text else location_text
                        
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
                        
                        # Extract category if possible
                        category = self._extract_category(title)
                        
                        # Add data to listings
                        self.listings.append({
                            'title': title,
                            'location': location,
                            'price': price_text,
                            'price_value': price_value,
                            'url': url,
                            'category': category
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
                        
                        # Extract price
                        price_element = item.select_one('div[data-role="price"]')
                        price_text = price_element.text.strip() if price_element else "0 zł"
                        
                        # Extract numeric price for analysis
                        price_value = self._extract_price(price_text)
                        
                        # Extract URL
                        url_element = item.select_one('a')
                        url = url_element['href'] if url_element and 'href' in url_element.attrs else "No URL"
                        
                        # Extract category if possible
                        category = self._extract_category(title)
                        
                        # Add data to listings
                        self.listings.append({
                            'title': title,
                            'location': location,
                            'price': price_text,
                            'price_value': price_value,
                            'url': url,
                            'category': category
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
            
    def count_listings_by_region(self, region):
        """Count listings from a specific region."""
        region_pattern = re.compile(region, re.IGNORECASE)
        count = sum(1 for listing in self.listings if region_pattern.search(listing['location']))
        return count
        
    def save_to_file(self, filename="ogloszenia.csv"):
        """Save the scraped data to a CSV file."""
        try:
            if not self.listings:
                print("No data to save")
                return False
                
            df = pd.DataFrame(self.listings)
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"Data saved to {filename}")
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
            
            report += f"""
## Region Analysis: {region}
Average price in {region}: {region_avg_price:.2f} zł
Average price in other regions: {other_avg_price:.2f} zł
Price difference: {price_diff:.2f} zł ({price_diff_pct:.1f}%)
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
- Region comparison: region_price_comparison.png

## Report Generated
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        return report
            
    def cleanup(self):
        """Close the browser and perform cleanup."""
        if self.driver:
            self.driver.quit()
            print("Browser closed")
            
    def run_scraper(self, search_phrase, region, pages=3, generate_charts=True, generate_report=True, report_format="txt"):
        """Run the full scraping process."""
        try:
            self.setup_driver()
            self.navigate_to_site()
            self.handle_popups()
            self.search_listings(search_phrase)
            
            # Scrape multiple pages
            page_count = 1
            while page_count <= pages:
                print(f"Scraping page {page_count}")
                self.scrape_page()
                
                if page_count < pages:
                    has_next = self.navigate_to_next_page()
                    if not has_next:
                        break
                page_count += 1
                
            # Count and report results
            region_count = self.count_listings_by_region(region)
            print(f"Found {region_count} listings containing \"{region}\"")
            
            # Save data
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