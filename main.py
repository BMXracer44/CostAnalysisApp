import tkinter as tk
from tkinter import scrolledtext, END, messagebox, Toplevel, Radiobutton, StringVar, LabelFrame
import threading
import queue
import re
from functools import partial

# --- Web Scraping and Logic ---

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import time
from bs4 import BeautifulSoup

def parse_price(price_text):
    """Extracts a float value from a price string like '$10.99'."""
    if not price_text:
        return 0.0
    match = re.search(r'\d+\.\d{2}|\d+', price_text)
    if match:
        return float(match.group())
    return 0.0

def get_aldi_results(url, results_list):
    """Scrapes Aldi in headless mode, adds top 5 results to a shared list."""
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)

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
        print(f"Error scraping Aldi: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

def get_walmart_results(url, results_list):
    """Scrapes Walmart in headless mode, adds top 5 results to a shared list."""
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)
        
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
                name = name_element.text.strip()
                price_text = price_element.text.strip()
                
                # Format Walmart prices like '632' to '$6.32'
                if price_text.isdigit() and len(price_text) > 4:
                    price_text = f"${price_text[:-4]}.{price_text[-4:]}"

                results_list.append({
                    'store': 'Walmart',
                    'name': name,
                    'price': price_text
                })
                count += 1
    except Exception as e:
        print(f"Error scraping Walmart: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

def get_target_results(url, results_list):
    """Scrapes Target in headless mode, adds top 5 results to a shared list."""
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)
        
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
        """Creates a pop-up window for the user to select one product PER store."""
        item_name = data['item_name']
        grouped_results = data['results']

        self.selection_window = Toplevel(self.root)
        self.selection_window.title(f"Select products for '{item_name}'")
        
        tk.Label(self.selection_window, text=f"Choose one option per store for '{item_name}'", pady=10).pack()
        
        self.radio_vars = {}
        
        for store in ["Aldi", "Walmart", "Target"]:
            store_results = grouped_results.get(store, [])
            if not store_results:
                continue

            frame = LabelFrame(self.selection_window, text=store, padx=10, pady=10)
            frame.pack(padx=10, pady=5, fill="x")

            self.radio_vars[store] = StringVar(value=None)
            
            for i, result in enumerate(store_results):
                text = f"{result['name']} - {result['price']}"
                Radiobutton(frame, text=text, variable=self.radio_vars[store], value=i, justify='left').pack(anchor='w')
            
            Radiobutton(frame, text="Skip this store", variable=self.radio_vars[store], value=-1, justify='left').pack(anchor='w', pady=(5,0))

        add_button = tk.Button(self.selection_window, text="Add Selections to Cart", command=partial(self.handle_selection, grouped_results))
        add_button.pack(pady=10)
        
        self.selection_window.transient(self.root)
        self.selection_window.grab_set()
        self.root.wait_window(self.selection_window)

    def handle_selection(self, grouped_results):
        """Processes the user's choices from each store's radio buttons."""
        choices = []
        for store, var in self.radio_vars.items():
            choice_index_str = var.get()
            if choice_index_str:
                choice_index = int(choice_index_str)
                if choice_index >= 0:
                    choices.append(grouped_results[store][choice_index])
        
        self.user_choice = choices
        self.selection_event.set()
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
            
            all_results = []
            threads = []
            
            scrapers_to_run = [
                (get_aldi_results, f"https://www.aldi.us/results?q={item}"),
                (get_walmart_results, f"https://www.walmart.com/search?q={item}"),
                (get_target_results, f"https://www.target.com/s?searchTerm={item}")
            ]

            for func, url in scrapers_to_run:
                thread = threading.Thread(target=func, args=(url, all_results))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            if not all_results:
                self.output_queue.put(("LOG", f"-> No results found for '{item}' at any store."))
                continue

            grouped_results = {'Aldi': [], 'Walmart': [], 'Target': []}
            for result in all_results:
                grouped_results[result['store']].append(result)

            self.selection_event.clear()
            self.output_queue.put(("PROMPT_SELECTION", {'item_name': item, 'results': grouped_results}))
            
            self.selection_event.wait()
            
            if self.user_choice:
                for choice in self.user_choice:
                    store = choice['store']
                    self.carts[store].append(choice)
                    self.output_queue.put(("LOG", f"-> Added '{choice['name']}' to {store} cart."))
            else:
                self.output_queue.put(("LOG", f"-> No products selected for item '{item}'."))
        
        self.output_queue.put(("FINALIZE", None))


if __name__ == '__main__':
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()