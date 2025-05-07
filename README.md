# ClassifiedScraper 

A Python tool for scraping classified advertisements from Polish websites (OLX and Allegro), with data analysis and visualization capabilities.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Interactive Interface Guide](#interactive-interface-guide)
- [Output Files](#output-files)
- [Charts Generated](#charts-generated)
- [Database](#database)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- Scrape classified ads from OLX.pl and Allegro.pl
- Search for multiple phrases in one run
- Extract listing details including titles, prices, locations, dates
- Extract and calculate price per square meter where applicable
- Save data to CSV and Excel files with summary statistics
- Store all data in SQLite database for long-term storage
- Generate visualizations including:
  - Price comparisons by location
  - Category distribution
  - Price distribution
  - Regional price comparisons
  - Price vs. size analysis
  - Highest price listings
  - Date distribution

## Requirements

- Python 3.6 or higher
- Chrome browser installed
- Internet connection

## Installation

1. Clone this repository or download the script:

```bash
git clone https://github.com/Moeez-03/web-scraper.git
cd web-scraper
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

If you don't have a requirements.txt file, create one with the following content:

```
pandas
matplotlib
seaborn
selenium
beautifulsoup4
webdriver-manager
openpyxl
numpy
```

Or install dependencies directly:

```bash
pip install pandas matplotlib seaborn selenium beautifulsoup4 webdriver-manager openpyxl numpy
```

## Usage

Run the script with Python:

```bash
python classifiedscraper.py
```

The program uses an interactive interface to collect user input for scraping parameters.

## Interactive Interface Guide

When you run the program, you'll be guided through a series of questions to configure the scraper:

### 1. Website Selection

```
Which site would you like to scrape?
1. OLX
2. Allegro
Enter your choice (1/2):
```

- Type `1` and press Enter to scrape OLX.pl
- Type `2` and press Enter to scrape Allegro.pl

### 2. Search Phrases

```
What would you like to search for?
You can enter multiple search phrases separated by commas
Enter search phrase(s):
```

- Enter a single search phrase like: `mieszkanie warszawa`
- Or enter multiple search phrases separated by commas: `mieszkanie warszawa, dom 100m2, lokal użytkowy`
- The scraper will process each search phrase separately

### 3. Number of Pages

```
How many pages should be scraped for each search phrase?
Enter number of pages (default is 3):
```

- Enter a number (e.g., `5`) to scrape that many pages for each search phrase
- Press Enter without typing anything to use the default value of 3 pages
- Higher values will get more listings but will take longer to run

### 4. Region for Analysis

```
Would you like to do a region-specific analysis?
Enter region name (or leave empty for no region analysis):
```

- Enter a region name like `Warszawa` or `Kraków` to generate region-specific comparisons
- Leave empty and press Enter if you don't want region-specific analysis
- The region name is used for pattern matching, so it's not case-sensitive

### 5. Confirmation

```
Scraping Configuration:
Site: olx
Search phrases: ['mieszkanie warszawa', 'dom 100m2']
Max pages per search: 5
Region analysis: Yes - Warszawa

Start scraping with these settings? (y/n):
```

- Review your settings and type `y` or `yes` (case-insensitive) to start scraping
- Type `n` or `no` to cancel and exit the program

## Output Files

After scraping, the program generates several output files:

1. **CSV files** named `<search_phrase>_<timestamp>.csv` containing all scraped listings

2. **Excel files** named `<search_phrase>_<timestamp>.xlsx` with two sheets:
   - `Listings` sheet with all scraped data
   - `Summary` sheet with statistics (average price, median price, etc.)

3. **Chart images** in the `charts` directory (created if it doesn't exist)

## Charts Generated

The program generates the following charts in the `charts` directory:

1. `avg_price_by_location.png` - Bar chart showing average prices in top 10 locations
2. `category_distribution.png` - Pie chart showing distribution of listings by category
3. `price_distribution.png` - Histogram of price distribution with mean and median lines
4. `region_comparison.png` - Comparison of prices in specified region vs other regions (if region was specified)
5. `price_per_sqm.png` - Scatter plot of price vs. square meters with regression line
6. `highest_prices.png` - Bar chart of top 10 most expensive listings
7. `date_distribution.png` - Distribution of listings by date posted

## Database

All scraped data is stored in an SQLite database file named `listings.db` which is created in the same directory as the script. This allows for data persistence across multiple scraping sessions.

The database contains a single table called `listings` with the following columns:
- id (primary key)
- title
- location
- price (text format)
- price_value (numeric)
- url
- date_posted
- category
- square_meters
- price_per_sqm
- search_phrase
- scraped_date

You can access this database using any SQLite client or in Python using the sqlite3 module.

## Troubleshooting

### Chrome Driver Issues

If you encounter issues with Chrome driver:
- Make sure you have Chrome browser installed
- The program uses webdriver-manager which should download the appropriate driver, but if it fails, try updating your Chrome browser

### Connection Errors

If you get connection errors:
- Check your internet connection
- The website might be blocking automated access - try reducing the number of pages
- Try running again later as the site might have temporary restrictions

### No Results

If the scraper doesn't find any results:
- Check your search phrase spelling
- Make sure you're using the correct site for your search
- Some specialized items might not be available on the selected platform

### Slow Performance

If the scraper is running slowly:
- Reduce the number of pages to scrape
- Use more specific search phrases
- Check your internet connection speed

## License

This project is available under the MIT License.