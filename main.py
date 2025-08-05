from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

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

def main():
    setup_driver()
    element_list = []

    for page in range(1, 3):
        # Initialize driver properly
        driver = webdriver.Firefox()

        # Load the URL
        url = f"https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page=%7Bpage%7D"
        driver.get(url)
        time.sleep(2)  # Optional wait to ensure page loads

        # Extract product details
        titles = driver.find_elements(By.CLASS_NAME, "title")
        prices = driver.find_elements(By.CLASS_NAME, "price")
        descriptions = driver.find_elements(By.CLASS_NAME, "description")
        ratings = driver.find_elements(By.CLASS_NAME, "ratings")

        # Store results in a list
        for i in range(len(titles)):
            element_list.append([
                titles[i].text,
                prices[i].text,
                descriptions[i].text,
                ratings[i].text
            ])

        driver.quit()

    # Display extracted data
    for row in element_list:
        print(row)

if __name__ == '__main__':
    main()