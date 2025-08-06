import tkinter as tk
from tkinter import scrolledtext, END, messagebox, Toplevel, Radiobutton, StringVar
import threading
import queue
import re
from functools import partial

# --- Web Scraping and Logic ---

from selenium import webdriver
import time
from bs4 import BeautifulSoup

def parse_price(price_text):
    """Extracts a float value from a price string like '$10.99'."""
    if not price_text:
        return 0.0
    # Find the first occurrence of a number (int or float) in the string
    match = re.search(r'\d+\.\d{2}|\d+', price_text)
    if match:
        return float(match.group())
    return 0.0

def get_aldi_results(url, results_list):
    """Scrapes Aldi, adds top 5 results to a shared list."""
    try:
        driver = webdriver.Firefox()
        driver.get(url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_tiles = soup.select('div[id^="product-tile-"]')
        
        count = 0
        for tile in product_tiles:
            if count >= 5: break
            name_element = tile.select_one('.product-tile__name')
            price_element = tile.select_one('.product-tile__price')
            if name_element and price_element:
                results_list.append({
                    'store': 'Aldi',
                    'name': name_element.text.strip(),
                    'price': price_element.text.strip()
                })
                count += 1
    except Exception as e:
        print(f"Error scraping Aldi: {e}") # Log error to console
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

def get_walmart_results(url, results_list):
    """Scrapes Walmart, adds top 5 results to a shared list."""
    try:
        driver = webdriver.Firefox()
        driver.get(url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_tiles = soup.select('div.mb0.ph0-xl.pt0-xl.bb.b--near-white.w-25.pb3-m.ph1')
        
        count = 0
        for tile in product_tiles:
            if count >= 5: break
            name_element = tile.select_one('span[data-automation-id="product-title"]')
            price_element = tile.select_one('div[data-automation-id="product-price"]')
            if name_element and price_element:
                results_list.append({
                    'store': 'Walmart',
                    'name': name_element.text.strip(),
                    'price': price_element.text.strip()
                })
                count += 1
    except Exception as e:
        print(f"Error scraping Walmart: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

def get_target_results(url, results_list):
    """Scrapes Target, adds top 5 results to a shared list."""
    try:
        driver = webdriver.Firefox()
        driver.get(url)
        time.sleep(10)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_tiles = soup.select('[data-test="@web/site-top-of-funnel/ProductCardWrapper"]')
        
        count = 0
        for tile in product_tiles:
            if count >= 5: break
            name_element = tile.select_one('[data-test="product-title"]')
            price_element = tile.select_one('span[data-test="current-price"] span')
            if name_element and price_element:
                results_list.append({
                    'store': 'Target',
                    'name': name_element.text.strip(),
                    'price': price_element.text.strip()
                })
                count += 1
    except Exception as e:
        print(f"Error scraping Target: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

# --- GUI Application Class ---

class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Shopping Comparator")
        self.root.geometry("700x550")

        # --- State Management ---
        self.output_queue = queue.Queue()
        self.selection_event = threading.Event()
        self.user_choice = None
        self.carts = {'Aldi': [], 'Walmart': [], 'Target': []}

        # --- Widgets ---
        top_frame = tk.Frame(self.root, pady=5)
        top_frame.pack(fill='x', padx=10, pady=5)
        
        self.item_label = tk.Label(top_frame, text="Enter Items (comma-separated):")
        self.item_label.pack(side='left')

        self.item_entry = tk.Entry(top_frame, width=40)
        self.item_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.item_entry.bind("<Return>", self.start_search)

        self.search_button = tk.Button(top_frame, text="Search All", command=self.start_search)
        self.search_button.pack(side='left')

        self.results_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state='disabled')
        self.results_text.pack(padx=10, pady=10, fill='both', expand=True)
        
        self.process_queue()

    def update_log(self, message):
        """Thread-safe method to append messages to the results box."""
        self.results_text.config(state='normal')
        self.results_text.insert(tk.END, message + "\n")
        self.results_text.see(END)
        self.results_text.config(state='disabled')

    def start_search(self, event=None):
        items_string = self.item_entry.get()
        item_list = [item.strip() for item in items_string.split(',') if item.strip()]
        if not item_list:
            messagebox.showwarning("Input Error", "Please enter at least one item.")
            return

        self.search_button.config(state='disabled')
        self.results_text.config(state='normal')
        self.results_text.delete('1.0', END)
        self.results_text.config(state='disabled')
        
        # Reset carts for a new search
        self.carts = {'Aldi': [], 'Walmart': [], 'Target': []}

        threading.Thread(target=self.run_shopping_flow, args=(item_list,)).start()

    def process_queue(self):
        """Processes commands from the scraper thread."""
        try:
            command, data = self.output_queue.get_nowait()
            if command == "LOG":
                self.update_log(data)
            elif command == "PROMPT_SELECTION":
                self.create_selection_window(data)
            elif command == "FINALIZE":
                self.generate_receipts()
                self.search_button.config(state='normal')
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def create_selection_window(self, data):
        """Creates a pop-up window for the user to select a product."""
        item_name = data['item_name']
        results = data['results']

        self.selection_window = Toplevel(self.root)
        self.selection_window.title(f"Select a product for '{item_name}'")
        
        tk.Label(self.selection_window, text=f"Found {len(results)} options for '{item_name}'. Please choose one:", pady=10).pack()
        
        self.radio_var = StringVar(value=None)
        
        for i, result in enumerate(results):
            text = f"{result['store']}: {result['name']} - {result['price']}"
            Radiobutton(self.selection_window, text=text, variable=self.radio_var, value=i, justify='left').pack(anchor='w', padx=10)
        
        # Option to skip adding this item
        Radiobutton(self.selection_window, text="Skip this item", variable=self.radio_var, value=-1, justify='left').pack(anchor='w', padx=10, pady=5)
        
        add_button = tk.Button(self.selection_window, text="Add to Cart", command=partial(self.handle_selection, results))
        add_button.pack(pady=10)
        
        # Make the main window wait for this one to close
        self.selection_window.transient(self.root)
        self.selection_window.grab_set()
        self.root.wait_window(self.selection_window)

    def handle_selection(self, results):
        """Processes the user's choice from the radio buttons."""
        choice_index = int(self.radio_var.get())
        
        if choice_index >= 0:
            self.user_choice = results[choice_index]
        else:
            self.user_choice = "SKIP" # User chose to skip

        self.selection_event.set() # Unpause the scraper thread
        self.selection_window.destroy()

    def generate_receipts(self):
        """Formats and displays the final receipts and cheapest store."""
        self.update_log("\n" + "="*40)
        self.update_log("        SHOPPING TRIP SUMMARY")
        self.update_log("="*40 + "\n")

        store_totals = {}

        for store, items in self.carts.items():
            self.update_log(f"--- {store} Receipt ---")
            if not items:
                self.update_log("  (No items selected for this store)\n")
                store_totals[store] = 0
                continue
            
            total = 0
            for item in items:
                price = parse_price(item['price'])
                total += price
                self.update_log(f"  - {item['name']}: ${price:.2f}")
            
            self.update_log(f"\n  {store} TOTAL: ${total:.2f}\n")
            store_totals[store] = total
        
        # Find the cheapest store, ignoring stores with no items
        valid_stores = {s: t for s, t in store_totals.items() if self.carts[s]}
        if not valid_stores:
            self.update_log("No items were selected to compare prices.")
            return

        cheapest_store = min(valid_stores, key=valid_stores.get)
        min_total = valid_stores[cheapest_store]
        
        self.update_log("--- Comparison ---")
        self.update_log(f"The cheapest store is {cheapest_store} with a total of ${min_total:.2f}.")

    def run_shopping_flow(self, item_list):
        """Main logic for the scraper thread."""
        for item in item_list:
            self.output_queue.put(("LOG", f"\n===== Searching for: {item.upper()} ====="))
            
            # This list will be shared by the scraper threads to deposit results
            all_results = []
            threads = []
            
            scrapers_to_run = [
                (get_aldi_results, f"https://www.aldi.us/results?q={item}"),
                (get_walmart_results, f"https://www.walmart.com/search?q={item}"),
                (get_target_results, f"https://www.target.com/s?searchTerm={item}")
            ]

            for func, url in scrapers_to_run:
                # Note: args must be a tuple, hence the comma in (all_results,)
                thread = threading.Thread(target=func, args=(url, all_results))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            if not all_results:
                self.output_queue.put(("LOG", f"-> No results found for '{item}' at any store."))
                continue

            # Signal GUI to ask for user's choice
            self.selection_event.clear()
            self.output_queue.put(("PROMPT_SELECTION", {'item_name': item, 'results': all_results}))
            
            # PAUSE here and wait for the user to make a selection in the GUI
            self.selection_event.wait()
            
            # RESUME after selection is made
            if self.user_choice and self.user_choice != "SKIP":
                store = self.user_choice['store']
                self.carts[store].append(self.user_choice)
                self.output_queue.put(("LOG", f"-> Added '{self.user_choice['name']}' to {store} cart."))
            else:
                self.output_queue.put(("LOG", f"-> Skipped item '{item}'."))
        
        # Signal GUI to finalize and print receipts
        self.output_queue.put(("FINALIZE", None))


if __name__ == '__main__':
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()