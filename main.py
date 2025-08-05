from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup

def setup_driver():
    """Initializes the driver options"""
    

    # Set up Chrome options (optional)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode (optional)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Use a proper Service object
    service = Service(ChromeDriverManager().install())

def get_user_item():
    user_item = input("Enter the item you wish to purchase: ")
    if(user_item != ''):
        return user_item
    print("Invalid item")
    return 0

def get_aldi_results(url):
    # Initialize driver properly
    driver = webdriver.Firefox()

    driver.get(url)
    time.sleep(5)  # Optional wait to ensure page loads
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find all the product tiles on the page
    product_tiles = soup.select('div[id^="product-tile-"]')

    # Loop through each tile
    for tile in product_tiles:
        # Find the name element within the tile
        name_element = tile.select_one('.product-tile__name')
        # Find the price element within the tile
        price_element = tile.select_one('.product-tile__price')

        # Get the text if the elements were found
        if name_element and price_element:
            name = name_element.text.strip()
            price_text = price_element.text.strip()
            # The parse_price function would then convert the text to a number
            price = price_text 
            
            print(f"Found: {name} for {price}")

    driver.quit()


def main():
    setup_driver()
    element_list = []

    # Get user item
    user_item = get_user_item();

    # Load the URL
    walmart = f"https://www.walmart.com/search?q=" + user_item
    target = "https://www.target.com/s?searchTerm=" + user_item
    aldi = "https://www.aldi.us/results?q=" + user_item

    get_aldi_results(aldi)

if __name__ == '__main__':
    main()