"""Browser setup and utility functions"""
import time
import random
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait


def create_driver():
    """Create and configure Chrome driver with anti-detection"""
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--start-minimized')
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def human_delay(min_sec=1.5, max_sec=3.0):
    """Random delay to mimic human behavior"""
    time.sleep(random.uniform(min_sec, max_sec))


def smooth_scroll(driver, element):
    """Smooth scroll to element"""
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
        element
    )
    time.sleep(random.uniform(0.8, 1.5))


def scroll_page_to_load(driver):
    """Scroll entire page to load all lazy-loaded content"""
    print("Scrolling page to load all content...")
    
    # Scroll down in increments
    for i in range(5):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1.5)
    
    # Scroll back to top
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)
