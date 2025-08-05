import requests
from bs4 import BeautifulSoup
import json
import random
import asyncio
from playwright.async_api import async_playwright

# --- User-Agent Rotation ---
# A list of user agents to rotate to avoid being blocked
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
]

def get_random_user_agent():
    """Returns a random user agent from the list."""
    return random.choice(USER_AGENTS)

# --- Scraper Functions ---

async def scrape_walmart(playwright, food_item):
    """Scrapes Walmart using Playwright to handle dynamic content."""
    print(f"Scraping Walmart for '{food_item}'...")
    url = f"https://www.walmart.com/search?q={food_item.replace(' ', '+')}"
    browser = await playwright.chromium.launch()
    page = await browser.new_page(user_agent=get_random_user_agent())
    try:
        await page.goto(url, wait_until='networkidle', timeout=60000)
        
        # Wait for the product grid to be visible
        await page.wait_for_selector('div[data-item-id]', timeout=15000)

        # Find the first product that contains the keyword
        all_products = await page.query_selector_all('div[data-item-id]')
        for product in all_products:
            name_element = await product.query_selector('span[data-automation-id="product-title"]')
            if name_element:
                name = await name_element.inner_text()
                if food_item.lower() in name.lower():
                    price_element = await product.query_selector('div[data-automation-id="product-price"] .f2')
                    if price_element:
                        price_text = await price_element.inner_text()
                        # Extract the numeric part of the price
                        price = float(price_text.replace('$', '').split()[0])
                        await browser.close()
                        return {'store': 'Walmart', 'name': name, 'price': price}

    except Exception as e:
        print(f"Error scraping Walmart: {e}")
    finally:
        await browser.close()
    
    print(f"Could not find '{food_item}' at Walmart.")
    return None

async def scrape_target(playwright, food_item):
    """Scrapes Target using Playwright."""
    print(f"Scraping Target for '{food_item}'...")
    url = f"https://www.target.com/s?searchTerm={food_item.replace(' ', '+')}"
    browser = await playwright.chromium.launch()
    page = await browser.new_page(user_agent=get_random_user_agent())
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        # Wait for the product cards to appear
        await page.wait_for_selector('[data-test="product-card"]', timeout=15000)

        product_cards = await page.query_selector_all('[data-test="product-card"]')
        for card in product_cards:
            name_element = await card.query_selector('[data-test="product-title"]')
            if name_element:
                name = await name_element.inner_text()
                if food_item.lower() in name.lower():
                    price_element = await card.query_selector('[data-test="current-price"]')
                    if price_element:
                        price_text = await price_element.inner_text()
                        price = float(price_text.replace('$', ''))
                        await browser.close()
                        return {'store': 'Target', 'name': name, 'price': price}

    except Exception as e:
        print(f"Error scraping Target: {e}")
    finally:
        await browser.close()
        
    print(f"Could not find '{food_item}' at Target.")
    return None

async def scrape_aldi(playwright, food_item):
    """Scrapes Aldi using Playwright."""
    print(f"Scraping Aldi for '{food_item}'...")
    url = f"https://www.aldi.us/en/products/search/?q={food_item.replace(' ', '%20')}"
    browser = await playwright.chromium.launch()
    page = await browser.new_page(user_agent=get_random_user_agent())
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        # Aldi might show a "no results" page or a list of products
        # We wait for the product tile selector
        await page.wait_for_selector('.product-tile', timeout=10000)
        
        product_tiles = await page.query_selector_all('.product-tile')
        for tile in product_tiles:
            name_element = await tile.query_selector('.product-tile__name')
            if name_element:
                name = await name_element.inner_text()
                if food_item.lower() in name.lower():
                    price_element = await tile.query_selector('.product-tile__price-value')
                    if price_element:
                        price_text = await price_element.inner_text()
                        price = float(price_text.replace('$', ''))
                        await browser.close()
                        return {'store': 'Aldi', 'name': name, 'price': price}

    except Exception as e:
        print(f"Error scraping Aldi: {e}")
    finally:
        await browser.close()
        
    print(f"Could not find '{food_item}' at Aldi.")
    return None


def scrape_kroger(food_item, api_key, client_secret):
    """Gets product data from Kroger's API. This does not need Playwright."""
    print(f"Searching Kroger for '{food_item}'...")
    if not api_key or not client_secret:
        print("Kroger API key or secret not provided. Skipping Kroger.")
        return None
        
    token_url = 'https://api.kroger.com/v1/connect/oauth2/token'
    product_url = 'https://api.kroger.com/v1/products'

    try:
        token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        token_data = {'grant_type': 'client_credentials', 'scope': 'product.compact'}
        token_response = requests.post(token_url, headers=token_headers, data=token_data, auth=(api_key, client_secret))
        token_response.raise_for_status()
        access_token = token_response.json().get('access_token')

        if access_token:
            product_headers = {'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
            product_params = {'filter.term': food_item, 'filter.limit': 1}
            product_response = requests.get(product_url, headers=product_headers, params=product_params)
            product_response.raise_for_status()
            products = product_response.json().get('data')
            
            if products:
                product = products[0]
                name = product.get('description')
                price_info = product.get('items', [{}])[0].get('price')
                if price_info:
                    price = price_info.get('regular')
                    return {'store': 'Kroger', 'name': name, 'price': price}

    except requests.exceptions.RequestException as e:
        print(f"Error with Kroger API: {e}")
    except (KeyError, IndexError) as e:
        print(f"Could not parse Kroger API data: {e}")
    print(f"Could not find '{food_item}' at Kroger.")
    return None

# --- Main Execution ---

async def main():
    """Main async function to run the scraper and compare prices."""
    food_item = input("Enter a food item to compare prices for: ")
    kroger_api_key = input("Enter your Kroger API client ID (or press Enter to skip): ")
    kroger_client_secret = ""
    if kroger_api_key:
        kroger_client_secret = input("Enter your Kroger API client secret: ")

    async with async_playwright() as p:
        # Run scrapers concurrently
        tasks = [
            scrape_walmart(p, food_item),
            scrape_target(p, food_item),
            scrape_aldi(p, food_item),
        ]
        
        # The Kroger function is synchronous, so we run it separately
        kroger_result = scrape_kroger(food_item, kroger_api_key, kroger_client_secret)
        
        results = await asyncio.gather(*tasks)
        if kroger_result:
            results.append(kroger_result)

    # Filter out None results
    results = [r for r in results if r]

    if not results:
        print(f"\nCould not find '{food_item}' at any of the stores.")
        return

    print("\n--- Price Comparison ---")
    for result in results:
        price_value = result.get('price', 0.0)
        if isinstance(price_value, (int, float)):
            print(f"{result['store']}: {result['name']} - ${price_value:.2f}")
        else:
            print(f"{result['store']}: {result['name']} - Price not available")

    valid_results = [r for r in results if isinstance(r.get('price'), (int, float))]
    
    if valid_results:
        best_option = min(valid_results, key=lambda x: x['price'])
        print("\n--- Best Option ---")
        print(f"The best price is at {best_option['store']} for {best_option['name']} at ${best_option['price']:.2f}")
    else:
        print("\nCould not determine the best option as no prices were found.")

if __name__ == '__main__':
    asyncio.run(main())
