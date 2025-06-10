from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import time

# Set up Selenium WebDriver
chrome_options = Options()
# Enable headless mode for faster scraping
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
service = Service()  # Use default ChromeDriver in PATH

driver = webdriver.Chrome(service=service, options=chrome_options)

all_data = []

# Open Zomato Kochi page
url = "https://www.zomato.com/jodhpur/air-force-area-restaurants?category=2&place_name=Rajasthan+High+Court+Gate+no.5%2C++Rajasthan+High+Ct+Rd%2C++Jodhpur"
driver.get(url)
time.sleep(3)  # Initial wait for page load

# Try to accept cookies if popup appears
try:
    accept_btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Accept")]'))
    )
    accept_btn.click()
    time.sleep(2)
except Exception:
    pass  # No cookie popup

all_data = []

def scroll_until_end():
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    while True:
        driver.execute_script("window.scrollBy(0, 3000);")  # Scroll by more pixels
        time.sleep(0.7)  # Reduce sleep time
        try:
            end_element = driver.find_element(By.XPATH, "//p[contains(text(), 'End of search results')]")
            if end_element.is_displayed():
                print("Reached end of results.")
                break
        except NoSuchElementException:
            pass
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            scroll_attempts += 1
            if scroll_attempts > 2:
                print("No more content loading.")
                break
            time.sleep(1)
        else:
            scroll_attempts = 0
        last_height = new_height

scroll_until_end()

# Wait for restaurant cards to load before scraping
try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'jumbo-tracker') or contains(@data-testid, 'restaurant-card')]"))
    )
except Exception as e:
    print("Restaurant cards did not load. Check page structure or network.")
    driver.quit()
    exit()

# Try both possible selectors for robustness
restaurant_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'jumbo-tracker') or contains(@data-testid, 'restaurant-card')]")
print(f"Total cafés found: {len(restaurant_cards)}")

if len(restaurant_cards) == 0:
    print("No restaurant cards found. Saving page HTML for debugging.")
    with open("debug_zomato_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    driver.quit()
    exit()

data = []

for i, card in enumerate(restaurant_cards):
    try:
        # Extract all possible data from the card in one go
        cafe_name = card.find_element(By.CSS_SELECTOR, "h4").text.strip() if card.find_elements(By.CSS_SELECTOR, "h4") else "Not Found"
        link_element = card.find_element(By.CSS_SELECTOR, "a") if card.find_elements(By.CSS_SELECTOR, "a") else None
        cafe_link = link_element.get_attribute("href") if link_element else "Not Found"
        address = card.find_element(By.CSS_SELECTOR, "p").text.strip() if card.find_elements(By.CSS_SELECTOR, "p") else "Not Found"
        # Try to get phone/email from card if available (rare on Zomato)
        contact = "Not Found"
        email = "Not Found"
        # Only open detail page if phone/email not found in card and link is valid
        if cafe_link != "Not Found":
            driver.execute_script("window.open(arguments[0]);", cafe_link)
            driver.switch_to.window(driver.window_handles[1])
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                # Try to get contact and email from detail page
                contact_elem = driver.find_elements(By.XPATH, "//a[contains(@href, 'tel:')]")
                if contact_elem:
                    contact = contact_elem[0].text.strip()
                email_elem = driver.find_elements(By.XPATH, "//a[contains(@href, 'mailto:')]")
                if email_elem:
                    email = email_elem[0].get_attribute('href').replace('mailto:', '').strip()
            except Exception as e:
                print(f"Error loading details for card {i}: {e}")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        data.append({
            "Name": cafe_name,
            "URL": cafe_link,
            "Address": address,
            "Phone Number": contact,
            "Email Id": email
        })
    except Exception as e:
        print(f"Error processing card {i}: {e}")
        continue

# Save more data (if available) and faster 
filename = "zomato_Rajasthan_cafes.csv"
df = pd.DataFrame(data)
df.to_csv(filename, index=False)
print(f"Data saved to '{filename}'")
driver.quit()
