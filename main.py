import tkinter as tk
from tkinter import scrolledtext, END, messagebox
import threading
import queue

# --- Original Code (with modifications for GUI integration) ---

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup

# This function was part of the original script but is not used by the scraping functions.
# It is kept here to adhere to the "no functionality change" instruction.
def setup_driver():
    """Initializes the driver options"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())

def get_aldi_results(url, output_queue):
    output_queue.put("Scraping Aldi...")
    try:
        driver = webdriver.Firefox()
        driver.get(url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_tiles = soup.select('div[id^="product-tile-"]')
        
        if not product_tiles:
            output_queue.put("  -> No results found on Aldi.")

        for tile in product_tiles:
            name_element = tile.select_one('.product-tile__name')
            price_element = tile.select_one('.product-tile__price')
            if name_element and price_element:
                name = name_element.text.strip()
                price = price_element.text.strip()
                output_queue.put(f"  - Aldi: {name} for {price}")
    except Exception as e:
        output_queue.put(f"  -> Error scraping Aldi: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

def get_walmart_results(url, output_queue):
    output_queue.put("Scraping Walmart...")
    try:
        # This selector is built from the class names you provided.
        product_tile_selector = 'div.mb0.ph0-xl.pt0-xl.bb.b--near-white.w-25.pb3-m.ph1'
        
        driver = webdriver.Firefox()
        driver.get(url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all the product tiles using the new selector.
        product_tiles = soup.select(product_tile_selector)
        
        if not product_tiles:
             output_queue.put("  -> No results found on Walmart.")

        for tile in product_tiles:
            # Find name and price elements using the new data-automation-id attributes.
            name_element = tile.select_one('span[data-automation-id="product-title"]')
            price_element = tile.select_one('div[data-automation-id="product-price"]')

            if name_element and price_element:
                name = name_element.text.strip()
                price = price_element.text.strip()
                output_queue.put(f"  - Walmart: {name} for {price}")
    except Exception as e:
        output_queue.put(f"  -> Error scraping Walmart: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

def get_target_results(url, output_queue):
    output_queue.put("Scraping Target...")
    try:
        driver = webdriver.Firefox()
        driver.get(url)
        time.sleep(10)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_tiles = soup.select('[data-test="@web/site-top-of-funnel/ProductCardWrapper"]')

        if not product_tiles:
             output_queue.put("  -> No results found on Target.")

        for tile in product_tiles:
            name_element = tile.select_one('[data-test="product-title"]')
            price_element = tile.select_one('span[data-test="current-price"] span')
            if name_element and price_element:
                name = name_element.text.strip()
                price = price_element.text.strip()
                output_queue.put(f"  - Target: {name} for {price}")
    except Exception as e:
        output_queue.put(f"  -> Error scraping Target: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

def scraping_main_logic(item_list, output_queue):
    """The core logic, adapted to loop through a list of items."""
    setup_driver()  # Original call maintained

    for item in item_list:
        output_queue.put(f"\n===== SEARCHING FOR: {item.upper()} =====")
        # Construct URLs
        walmart = f"https://www.walmart.com/search?q={item}"
        target = f"https://www.target.com/s?searchTerm={item}"
        aldi = f"https://www.aldi.us/results?q={item}"

        # Run scrapers for the current item
        get_aldi_results(aldi, output_queue)
        get_walmart_results(walmart, output_queue)
        get_target_results(target, output_queue)
    
    output_queue.put("\n--- All Searches Complete ---")

# --- GUI Application Class ---

class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Web Scraper")
        self.root.geometry("600x500")

        self.output_queue = queue.Queue()

        # --- Widgets ---
        # Frame for input
        top_frame = tk.Frame(self.root, pady=5)
        top_frame.pack(fill='x', padx=10, pady=5)

        # Updated Input Label and Entry
        self.item_label = tk.Label(top_frame, text="Enter Items (comma-separated):")
        self.item_label.pack(side='left')

        self.item_entry = tk.Entry(top_frame, width=40)
        self.item_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.item_entry.bind("<Return>", self.start_search_thread)

        # Search Button
        self.search_button = tk.Button(top_frame, text="Search All", command=self.start_search_thread)
        self.search_button.pack(side='left')

        # Results Text Area
        self.results_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state='disabled')
        self.results_text.pack(padx=10, pady=10, fill='both', expand=True)
        
        # Start checking the queue for messages
        self.process_queue()

    def start_search_thread(self, event=None):
        """Starts the scraping process in a new thread to keep the GUI responsive."""
        items_string = self.item_entry.get()
        # Create a list of items, stripping whitespace and ignoring empty entries
        item_list = [item.strip() for item in items_string.split(',') if item.strip()]

        if not item_list:
            messagebox.showwarning("Input Error", "Please enter at least one item to search for.")
            return

        self.search_button.config(state='disabled')
        self.results_text.config(state='normal')
        self.results_text.delete('1.0', END)
        self.results_text.insert(tk.END, f"Beginning search for {len(item_list)} item(s)...\n")
        self.results_text.config(state='disabled')

        # Run the blocking scraping task in a separate thread
        self.search_thread = threading.Thread(
            target=scraping_main_logic, 
            args=(item_list, self.output_queue)
        )
        self.search_thread.start()

    def process_queue(self):
        """Checks the queue for messages from the scraper thread and updates the GUI."""
        try:
            while True:
                message = self.output_queue.get_nowait()
                self.results_text.config(state='normal')
                self.results_text.insert(tk.END, message + "\n")
                self.results_text.see(END)  # Auto-scroll
                self.results_text.config(state='disabled')

                if "--- All Searches Complete ---" in message:
                    self.search_button.config(state='normal')

        except queue.Empty:
            pass  # No new messages
        
        # Check again after 100ms
        self.root.after(100, self.process_queue)


if __name__ == '__main__':
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()