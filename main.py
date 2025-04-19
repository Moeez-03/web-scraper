import time
import pandas as pd
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
from webdriver_manager.chrome import ChromeDriverManager

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
                        price = price_element.text.strip() if price_element else "No Price"
                        
                        # Extract URL
                        url_element = item.select_one('a')
                        url = url_element['href'] if url_element and 'href' in url_element.attrs else "No URL"
                        if url.startswith('/'):
                            url = f"https://www.olx.pl{url}"
                        
                        # Add data to listings
                        self.listings.append({
                            'title': title,
                            'location': location,
                            'price': price,
                            'url': url
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
                        price = price_element.text.strip() if price_element else "No Price"
                        
                        # Extract URL
                        url_element = item.select_one('a')
                        url = url_element['href'] if url_element and 'href' in url_element.attrs else "No URL"
                        
                        # Add data to listings
                        self.listings.append({
                            'title': title,
                            'location': location,
                            'price': price,
                            'url': url
                        })
                        
                    except Exception as e:
                        print(f"Error scraping individual listing: {e}")
                        continue
                        
            print(f"Scraped {len(self.listings)} listings so far")
            
        except Exception as e:
            print(f"Error scraping page: {e}")
            
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
            
    def cleanup(self):
        """Close the browser and perform cleanup."""
        if self.driver:
            self.driver.quit()
            print("Browser closed")
            
    def run_scraper(self, search_phrase, region, pages=3):
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
            
        except Exception as e:
            print(f"Error running scraper: {e}")
        finally:
            self.cleanup()
            
def main():
    """Main function to run the scraper."""
    print("=" * 50)
    print("Classified Ads Scraper")
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
        
    # Initialize and run scraper
    scraper = ClassifiedScraper(site)
    scraper.run_scraper(search_phrase, region, pages)

if __name__ == "__main__":
    main()