from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import random
import time
import json
import logging
import os
import sys
from typing import Dict, Optional
from colorama import init, Fore, Style
import pyfiglet
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from datetime import datetime
from cryptography.fernet import Fernet
from selenium.webdriver import Firefox, Edge
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
import pyotp
import requests
import imaplib
import email
from email.header import decode_header
import cv2
import numpy as np
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import atexit
from selenium.webdriver.support.select import Select
import re

class PRBot:
    def __init__(self, browser_type='chrome', use_proxy: bool = False, proxy: str = None):
        # Initialize colorama for Windows
        init()
        
        self.user_info = None
        self.setup_logging()
        self.load_config()
        self.data_dir = self.setup_data_directory()
        self.setup_encryption()
        self.browser_type = browser_type
        try:
            self.setup_browser(use_proxy, proxy)
            self.setup_2fa()
            # Register cleanup function
            atexit.register(self.cleanup)
        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}")
            raise

    def setup_logging(self):
        """Setup logging configuration"""
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        log_file = f'logs/pr_bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            self.config = {"common_form_fields": {}}

    def setup_encryption(self):
        """Setup encryption for sensitive data"""
        key_file = 'encryption.key'
        if not os.path.exists(key_file):
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
        else:
            with open(key_file, 'rb') as f:
                key = f.read()
        self.cipher_suite = Fernet(key)

    def setup_browser(self, use_proxy: bool, proxy: str):
        """Setup selected browser with options"""
        try:
            options = Options()
            if use_proxy and proxy:
                options.add_argument(f'--proxy-server={proxy}')
            
            # Add additional Chrome options for stability
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
            # Add random user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            ]
            options.add_argument(f'user-agent={random.choice(user_agents)}')
            
            # Create service object
            service = Service(ChromeDriverManager().install())
            
            # Initialize WebDriver with service and options
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(10)

        except Exception as e:
            self.logger.error(f"Browser setup error: {str(e)}")
            raise

    def setup_2fa(self):
        """Setup 2FA handling"""
        self.totp = None
        if 'totp_secret' in self.config:
            self.totp = pyotp.TOTP(self.config['totp_secret'])

    def display_banner(self):
        """Display PR BOT banner"""
        # Clear the screen first
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Create the banner with a different font
        banner = pyfiglet.figlet_format("PR BOT", font="slant")
        
        # Print the banner with colors
        print(Fore.CYAN + banner + Style.RESET_ALL)
        print(Fore.YELLOW + "=" * 50 + Style.RESET_ALL)
        print(Fore.YELLOW + "Welcome to PR BOT - Interactive Signup Assistant" + Style.RESET_ALL)
        print(Fore.YELLOW + "=" * 50 + Style.RESET_ALL)
        print("\n")

    def interactive_menu(self):
        """Display interactive menu"""
        while True:
            try:
                print(Fore.GREEN + "\nAvailable commands:" + Style.RESET_ALL)
                print("1. Enter user information")
                print("2. Start PR signup process")
                print("3. View current user info")
                print("4. View/Edit form fields")
                print("5. View logs")
                print("6. Manage sites")
                print(Fore.RED + "0. Exit" + Style.RESET_ALL)
                
                choice = input("\nEnter your choice (0-6): ")
                
                if choice == "1":
                    self.enter_user_info_manually()
                elif choice == "2":
                    if not self.user_info:
                        print(Fore.RED + "Please enter user information first!" + Style.RESET_ALL)
                        continue
                    self.start_signup_process()
                elif choice == "3":
                    self.view_current_info()
                elif choice == "4":
                    self.edit_form_fields()
                elif choice == "5":
                    self.view_logs()
                elif choice == "6":
                    self.manage_sites()
                elif choice == "0":
                    print(Fore.YELLOW + "\nThank you for using PR BOT. Goodbye!" + Style.RESET_ALL)
                    break
                else:
                    print(Fore.RED + "Invalid choice!" + Style.RESET_ALL)
                    
            except KeyboardInterrupt:
                print(Fore.YELLOW + "\nOperation cancelled by user." + Style.RESET_ALL)
                continue

    def enter_user_info_manually(self):
        """Manually enter user information with validation"""
        try:
            user_info = {}
            print("\nEntering user information:")
            
            # Define fields with their validation rules
            fields = {
                "username": {"prompt": "Username: ", "required": True},
                "email": {"prompt": "Email: ", "required": True},
                "password": {"prompt": "Password: ", "required": True},
                "first_name": {"prompt": "First Name: ", "required": True},
                "last_name": {"prompt": "Last Name: ", "required": True},
                "phone": {"prompt": "Phone (XXX-XXX-XXXX): ", "pattern": r'^\d{3}-\d{3}-\d{4}$'},
                "address": {"prompt": "Address: ", "required": True},
                "birth_date": {"prompt": "Birth Date (YYYY-MM-DD): ", "pattern": r'^\d{4}-\d{2}-\d{2}$'},
                "ssn": {"prompt": "SSN (XXX-XX-XXXX): ", "pattern": r'^\d{3}-\d{2}-\d{4}$'},
                "zip_code": {"prompt": "ZIP Code: ", "pattern": r'^\d{5}$'},
                "city": {"prompt": "City: ", "required": True},
                "state": {"prompt": "State (2 letters): ", "pattern": r'^[A-Z]{2}$'}
            }
            
            for field, rules in fields.items():
                while True:
                    value = prompt(Fore.CYAN + rules["prompt"] + Style.RESET_ALL)
                    
                    if not value and rules.get("required", False):
                        print(Fore.RED + f"{field} is required!" + Style.RESET_ALL)
                        continue
                        
                    if value and "pattern" in rules:
                        if not re.match(rules["pattern"], value):
                            print(Fore.RED + f"Invalid format for {field}!" + Style.RESET_ALL)
                            continue
                    
                    user_info[field] = value
                    break
            
            self.user_info = user_info
            print(Fore.GREEN + "\nUser information saved successfully!" + Style.RESET_ALL)
            return user_info
            
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\nInput cancelled by user." + Style.RESET_ALL)
            return None
        except Exception as e:
            self.logger.error(f"Error entering user info: {str(e)}")
            print(Fore.RED + f"Error: {str(e)}" + Style.RESET_ALL)
            return None

    def start_signup_process(self):
        """Start the signup process using stored sites"""
        if not self.user_info:
            print(Fore.RED + "Please enter user information first!" + Style.RESET_ALL)
            return

        active_sites = [site for site in self.load_sites() if site["enabled"]]
        if not active_sites:
            print(Fore.RED + "No active sites found!" + Style.RESET_ALL)
            return

        print("\nAvailable sites:")
        for i, site in enumerate(active_sites, 1):
            print(f"{i}. {site['name']} ({site['type']})")

        try:
            choice = input("\nEnter site number (or 'all' for all sites): ").lower()
            
            if choice == 'all':
                for site in active_sites:
                    print(f"\nProcessing {site['name']}...")
                    if site['name'] == "ListYourself":
                        success = self.signup_listyourself(self.user_info)
                    else:
                        success = self.signup(site['url'], self.user_info)
                    
                    if success:
                        print(Fore.GREEN + f"✓ {site['name']} signup successful!" + Style.RESET_ALL)
                    else:
                        print(Fore.RED + f"✗ {site['name']} signup failed!" + Style.RESET_ALL)
                    time.sleep(random.uniform(2, 5))
            else:
                index = int(choice) - 1
                if 0 <= index < len(active_sites):
                    site = active_sites[index]
                    if site['name'] == "ListYourself":
                        success = self.signup_listyourself(self.user_info)
                    else:
                        success = self.signup(site['url'], self.user_info)
                    
                    if success:
                        print(Fore.GREEN + f"✓ {site['name']} signup successful!" + Style.RESET_ALL)
                    else:
                        print(Fore.RED + f"✗ {site['name']} signup failed!" + Style.RESET_ALL)
                else:
                    print(Fore.RED + "Invalid site number!" + Style.RESET_ALL)
                
        except ValueError:
            print(Fore.RED + "Please enter a valid number!" + Style.RESET_ALL)

    def process_single_signup(self, url):
        """Process signup for a single URL"""
        try:
            print(Fore.CYAN + f"\nProcessing signup for: {url}" + Style.RESET_ALL)
            
            # Add delay before starting
            time.sleep(random.uniform(1, 2))
            
            success = self.signup(url, self.user_info)
            
            if success:
                print(Fore.GREEN + "✓ Signup completed successfully!" + Style.RESET_ALL)
            else:
                print(Fore.RED + "✗ Signup failed or couldn't be verified." + Style.RESET_ALL)
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error in signup process: {str(e)}")
            print(Fore.RED + f"Error: {str(e)}" + Style.RESET_ALL)
            return False

    def process_multiple_signups(self, urls):
        """Process signup for multiple URLs"""
        total = len(urls)
        successful = 0
        failed = 0
        
        print(Fore.CYAN + f"\nStarting signup process for {total} URLs" + Style.RESET_ALL)
        
        for i, url in enumerate(urls, 1):
            print(f"\nProcessing URL {i}/{total}: {url}")
            
            try:
                success = self.signup(url, self.user_info)
                
                if success:
                    successful += 1
                    print(Fore.GREEN + "✓ Success!" + Style.RESET_ALL)
                else:
                    failed += 1
                    print(Fore.RED + "✗ Failed!" + Style.RESET_ALL)
                
                # Add delay between signups
                if i < total:
                    delay = random.uniform(2, 5)
                    print(f"Waiting {delay:.1f} seconds before next signup...")
                    time.sleep(delay)
                    
            except Exception as e:
                failed += 1
                self.logger.error(f"Error processing {url}: {str(e)}")
                print(Fore.RED + f"Error: {str(e)}" + Style.RESET_ALL)
        
        # Print summary
        print(f"\nSignup Summary:")
        print(f"Total URLs: {total}")
        print(Fore.GREEN + f"Successful: {successful}" + Style.RESET_ALL)
        print(Fore.RED + f"Failed: {failed}" + Style.RESET_ALL)

    def log_signup_result(self, url, success):
        """Log signup result to a simple text file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = "SUCCESS" if success else "FAILED"
        log_entry = f"{timestamp} | {url} | {result}\n"
        
        with open(f"{self.data_dir}/signup_log.txt", 'a') as f:
            f.write(log_entry)

    def view_logs(self):
        """View recent logs"""
        log_dir = 'logs'
        log_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.log')], reverse=True)
        
        if not log_files:
            print("No logs found.")
            return
            
        print("\nRecent logs:")
        for i, log_file in enumerate(log_files[:5], 1):
            print(f"{i}. {log_file}")
        
        choice = input("\nEnter log number to view (or press Enter to skip): ")
        if choice.isdigit() and 1 <= int(choice) <= len(log_files):
            with open(os.path.join(log_dir, log_files[int(choice)-1]), 'r') as f:
                print("\n" + f.read())

    def random_delay(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """Add random delay between actions to appear more human-like"""
        time.sleep(random.uniform(min_delay, max_delay))
    
    def handle_captcha(self):
        """Placeholder for CAPTCHA handling"""
        self.logger.info("CAPTCHA detected! Please solve it manually.")
        input("Press Enter after solving the CAPTCHA...")
    
    def signup(self, url: str, user_info: Dict, form_data: Optional[Dict] = None) -> bool:
        """
        Perform signup on a website using provided user information
        :param url: Website URL
        :param user_info: Dictionary containing user's personal information
        :param form_data: Dictionary containing form field mappings
        """
        try:
            # Navigate to signup page
            self.logger.info(f"Navigating to {url}")
            self.driver.get(url)
            time.sleep(2)  # Wait for page to load
            
            if form_data is None:
                form_data = self.config.get("common_form_fields", {})
            
            # Fill in the form
            for field, xpath in form_data.items():
                if field in user_info and user_info[field]:
                    try:
                        # Wait for element to be present and interactable
                        element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        element = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        
                        # Clear any existing text
                        element.clear()
                        
                        # Type like a human with random delays between characters
                        for char in user_info[field]:
                            element.send_keys(char)
                            time.sleep(random.uniform(0.1, 0.3))
                        
                        self.logger.info(f"Filled {field} successfully")
                        time.sleep(random.uniform(0.5, 1.0))
                        
                    except Exception as e:
                        self.logger.error(f"Error filling field {field}: {str(e)}")
                        # Continue with other fields even if one fails
                        continue
            
            # Look for submit button with different possible selectors
            submit_buttons = [
                '//button[@type="submit"]',
                '//input[@type="submit"]',
                '//button[contains(text(), "Submit")]',
                '//button[contains(text(), "Sign Up")]',
                '//button[contains(text(), "Register")]',
                '//input[@value="Submit"]',
                '//input[@value="Sign Up"]',
                '//input[@value="Register"]'
            ]
            
            submit_button = None
            for button_xpath in submit_buttons:
                try:
                    submit_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, button_xpath))
                    )
                    if submit_button:
                        break
                except:
                    continue
            
            if submit_button:
                # Scroll submit button into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                time.sleep(1)
                
                # Click the submit button
                submit_button.click()
                self.logger.info("Form submitted")
                
                # Wait for success indicators
                success_indicators = [
                    '//div[contains(@class, "success")]',
                    '//div[contains(text(), "success")]',
                    '//div[contains(text(), "Success")]',
                    '//div[contains(text(), "thank you")]',
                    '//div[contains(text(), "Thank You")]'
                ]
                
                try:
                    for indicator in success_indicators:
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, indicator))
                            )
                            self.logger.info("Signup successful!")
                            return True
                        except:
                            continue
                    
                    # If no success indicator found, check URL change
                    time.sleep(3)
                    if self.driver.current_url != url:
                        self.logger.info("URL changed after submission - assuming success")
                        return True
                    
                except Exception as e:
                    self.logger.warning(f"Could not verify success: {str(e)}")
                    return False
            else:
                self.logger.error("Could not find submit button")
                return False
            
        except Exception as e:
            self.logger.error(f"Error during signup: {str(e)}")
            self.capture_screenshot(f"error_{int(time.time())}.png")
            return False

    def close(self):
        """Close the browser safely"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except Exception as e:
            self.logger.error(f"Error closing browser: {str(e)}")
            # Don't raise the exception to allow clean exit

    def handle_2fa(self):
        """Handle 2FA verification"""
        if self.totp:
            return self.totp.now()
        else:
            return input("Enter 2FA code: ")

    def verify_email(self, email_address, password, imap_server):
        """Verify email for registration"""
        try:
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_address, password)
            mail.select("inbox")
            
            # Search for verification email
            _, messages = mail.search(None, '(SUBJECT "Verify your account")')
            
            if messages[0]:
                latest_email_id = messages[0].split()[-1]
                _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
                email_body = msg_data[0][1]
                
                # Parse verification link
                email_message = email.message_from_bytes(email_body)
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/html":
                            body = part.get_payload(decode=True).decode()
                            # Extract and click verification link
                            verification_link = self.extract_verification_link(body)
                            if verification_link:
                                self.driver.get(verification_link)
                                return True
            return False
        except Exception as e:
            self.logger.error(f"Email verification failed: {str(e)}")
            return False

    def detect_form_fields(self):
        """Automatically detect form fields on the page"""
        form_fields = {}
        input_elements = self.driver.find_elements(By.TAG_NAME, "input")
        
        for element in input_elements:
            field_type = element.get_attribute("type")
            field_name = element.get_attribute("name")
            field_id = element.get_attribute("id")
            
            if field_type in ["text", "email", "password", "tel"]:
                form_fields[field_name or field_id] = element.get_attribute("xpath")
        
        return form_fields

    def capture_screenshot(self, error_message):
        """Capture screenshot on failure"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"logs/error_{timestamp}.png"
        self.driver.save_screenshot(screenshot_path)
        self.logger.error(f"Screenshot saved: {screenshot_path}")
        
        # Analyze screenshot for error messages using OCR
        img = cv2.imread(screenshot_path)
        # Add OCR logic here if needed

    def rotate_proxy(self):
        """Rotate proxy from proxy list"""
        if 'proxy_list' in self.config:
            return random.choice(self.config['proxy_list'])
        return None

    def backup_data(self):
        """Backup user data and configurations"""
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/backup_{timestamp}.zip"
        
        # Add backup logic here
        
    def restore_data(self, backup_file):
        """Restore data from backup"""
        if os.path.exists(backup_file):
            # Add restore logic here
            pass

    def edit_form_fields(self):
        """Edit form field mappings"""
        try:
            print("\nCurrent form fields:")
            for field, xpath in self.config["common_form_fields"].items():
                print(f"{field}: {xpath}")
            
            print("\nOptions:")
            print("1. Add field")
            print("2. Edit field")
            print("3. Remove field")
            print("0. Back")
            
            choice = input("\nEnter choice (0-3): ")
            
            if choice == "1":
                field = input("Enter field name: ")
                xpath = input("Enter xpath: ")
                self.config["common_form_fields"][field] = xpath
            elif choice == "2":
                field = input("Enter field name to edit: ")
                if field in self.config["common_form_fields"]:
                    xpath = input("Enter new xpath: ")
                    self.config["common_form_fields"][field] = xpath
                else:
                    print(Fore.RED + "Field not found!" + Style.RESET_ALL)
            elif choice == "3":
                field = input("Enter field name to remove: ")
                if field in self.config["common_form_fields"]:
                    del self.config["common_form_fields"][field]
                else:
                    print(Fore.RED + "Field not found!" + Style.RESET_ALL)
            
            # Save changes
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
            
        except Exception as e:
            self.logger.error(f"Error editing form fields: {str(e)}")
            print(Fore.RED + f"Error: {str(e)}" + Style.RESET_ALL)

    def setup_data_directory(self):
        """Setup directory for storing data"""
        data_dir = 'pr_bot_data'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir

    def save_user_info(self, user_info: Dict):
        """Save user info to a simple text file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.data_dir}/user_info_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            for key, value in user_info.items():
                f.write(f"{key}: {value}\n")
        
        print(Fore.GREEN + f"User info saved to: {filename}" + Style.RESET_ALL)

    def load_user_info_from_file(self, filename):
        """Load user info from a text file"""
        user_info = {}
        with open(filename, 'r') as f:
            for line in f:
                key, value = line.strip().split(': ', 1)
                user_info[key] = value
        return user_info

    def view_current_info(self):
        """View current user information"""
        if not self.user_info:
            print(Fore.RED + "No user information entered yet!" + Style.RESET_ALL)
            return
            
        print("\nCurrent user information:")
        for field, value in self.user_info.items():
            if field == "password":
                value = "*" * len(value)  # Mask password
            print(f"{field}: {value}")

    def cleanup(self):
        """Cleanup function to be called on exit"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except Exception:
            pass

    def signup_listyourself(self, user_info: Dict) -> bool:
        """Handle signup specifically for ListYourself.net"""
        try:
            url = "https://www.listyourself.net/ListYourself/listing.jsp"
            self.driver.get(url)
            time.sleep(2)  # Wait for page load

            # Form field mappings for ListYourself.net
            form_fields = {
                'phone': '//input[@name="phone"]',  # Phone number field
                'business_type': '//input[@value="business"]',  # Business radio button
                'name': '//input[@name="name"]',
                'country': '//select[@name="country"]',
                'address': '//input[@name="address"]',
                'city_state_zip': '//input[@name="city_state_zip"]',
                'email': '//input[@name="email"]',
                'confirm_email': '//input[@name="confirm_email"]',
                'validation_type': '//input[@value="call_me"]'  # Call Me radio button
            }

            # Fill in the form fields
            for field, xpath in form_fields.items():
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    
                    if field == 'country':
                        # Handle dropdown for country
                        select = Select(element)
                        select.select_by_visible_text('United States')
                    elif field == 'business_type':
                        # Click the Business radio button
                        if not element.is_selected():
                            element.click()
                    elif field == 'validation_type':
                        # Click the Call Me radio button
                        if not element.is_selected():
                            element.click()
                    else:
                        # Type like a human for text fields
                        element.clear()
                        for char in user_info[field]:
                            element.send_keys(char)
                            time.sleep(random.uniform(0.1, 0.3))

                    time.sleep(random.uniform(0.5, 1.0))
                    
                except Exception as e:
                    self.logger.error(f"Error filling field {field}: {str(e)}")
                    continue

            # Look for submit button
            submit_buttons = [
                '//button[contains(text(), "List Yourself!")]',
                '//input[@type="submit"]',
                '//button[@type="submit"]'
            ]

            for button_xpath in submit_buttons:
                try:
                    submit_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, button_xpath))
                    )
                    submit_button.click()
                    break
                except:
                    continue

            # Wait for confirmation
            try:
                confirmation = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "confirmation")]'))
                )
                return True
            except:
                self.logger.error("Could not verify signup completion")
                return False

        except Exception as e:
            self.logger.error(f"Error in ListYourself signup: {str(e)}")
            return False

    def get_user_info(self) -> Dict:
        """Get user information interactively"""
        user_info = {}
        
        print("\nPlease enter the following information:")
        
        fields = {
            'phone': 'Phone number (format: XXX-XXX-XXXX): ',
            'name': 'Business name: ',
            'address': 'Street address: ',
            'city_state_zip': 'City, State & Zip: ',
            'email': 'Email address: '
        }
        
        for field, prompt in fields.items():
            while True:
                value = input(Fore.CYAN + prompt + Style.RESET_ALL)
                
                # Validation
                if field == 'phone':
                    if not re.match(r'^\d{3}-\d{3}-\d{4}$', value):
                        print(Fore.RED + "Invalid phone format. Please use XXX-XXX-XXXX" + Style.RESET_ALL)
                        continue
                elif field == 'email':
                    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                        print(Fore.RED + "Invalid email format" + Style.RESET_ALL)
                        continue
                    user_info['confirm_email'] = value  # Auto-fill confirm email
                
                user_info[field] = value
                break
        
        return user_info

    def load_sites(self):
        """Load PR sites from sites.json"""
        try:
            if not os.path.exists('sites.json'):
                # Create default sites file if it doesn't exist
                default_sites = {
                    "active_sites": [
                        {
                            "name": "ListYourself",
                            "url": "https://www.listyourself.net/ListYourself/listing.jsp",
                            "type": "primary",
                            "enabled": True
                        }
                    ],
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open('sites.json', 'w') as f:
                    json.dump(default_sites, f, indent=4)
            
            with open('sites.json', 'r') as f:
                self.sites = json.load(f)
                return self.sites["active_sites"]
        except Exception as e:
            self.logger.error(f"Error loading sites: {str(e)}")
            return []

    def manage_sites(self):
        """Manage PR signup sites"""
        while True:
            print("\nSite Management:")
            print("1. View active sites")
            print("2. Add new site")
            print("3. Enable/Disable site")
            print("4. Update existing site")
            print("5. Back to main menu")
            
            choice = input("\nEnter choice (1-5): ")
            
            if choice == "1":
                self.view_sites()
            elif choice == "2":
                self.add_site()
            elif choice == "3":
                self.toggle_site()
            elif choice == "4":
                self.update_site()
            elif choice == "5":
                break
            else:
                print(Fore.RED + "Invalid choice!" + Style.RESET_ALL)

    def view_sites(self):
        """View all PR signup sites"""
        sites = self.load_sites()
        print("\nCurrent PR Sites:")
        print("-" * 50)
        for i, site in enumerate(sites, 1):
            status = Fore.GREEN + "Enabled" if site["enabled"] else Fore.RED + "Disabled"
            print(f"{i}. {site['name']}")
            print(f"   URL: {site['url']}")
            print(f"   Type: {site['type']}")
            print(f"   Status: {status}" + Style.RESET_ALL)
            print("-" * 50)

    def add_site(self):
        """Add a new PR signup site"""
        try:
            print("\nAdd New Site:")
            name = input("Enter site name: ")
            url = input("Enter site URL: ")
            site_type = input("Enter site type (primary/secondary): ").lower()
            
            new_site = {
                "name": name,
                "url": url,
                "type": site_type,
                "enabled": True
            }
            
            self.sites["active_sites"].append(new_site)
            self.sites["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open('sites.json', 'w') as f:
                json.dump(self.sites, f, indent=4)
            
            print(Fore.GREEN + "Site added successfully!" + Style.RESET_ALL)
            
        except Exception as e:
            print(Fore.RED + f"Error adding site: {str(e)}" + Style.RESET_ALL)

    def toggle_site(self):
        """Enable or disable a site"""
        self.view_sites()
        try:
            index = int(input("\nEnter site number to toggle: ")) - 1
            if 0 <= index < len(self.sites["active_sites"]):
                self.sites["active_sites"][index]["enabled"] = not self.sites["active_sites"][index]["enabled"]
                self.sites["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with open('sites.json', 'w') as f:
                    json.dump(self.sites, f, indent=4)
                
                status = "enabled" if self.sites["active_sites"][index]["enabled"] else "disabled"
                print(Fore.GREEN + f"Site {status} successfully!" + Style.RESET_ALL)
            else:
                print(Fore.RED + "Invalid site number!" + Style.RESET_ALL)
        except ValueError:
            print(Fore.RED + "Please enter a valid number!" + Style.RESET_ALL)

    def update_site(self):
        """Update existing site information"""
        self.view_sites()
        try:
            index = int(input("\nEnter site number to update: ")) - 1
            if 0 <= index < len(self.sites["active_sites"]):
                site = self.sites["active_sites"][index]
                print("\nLeave blank to keep current value")
                
                name = input(f"Name [{site['name']}]: ")
                url = input(f"URL [{site['url']}]: ")
                site_type = input(f"Type [{site['type']}]: ")
                
                if name: site['name'] = name
                if url: site['url'] = url
                if site_type: site['type'] = site_type.lower()
                
                self.sites["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with open('sites.json', 'w') as f:
                    json.dump(self.sites, f, indent=4)
                
                print(Fore.GREEN + "Site updated successfully!" + Style.RESET_ALL)
            else:
                print(Fore.RED + "Invalid site number!" + Style.RESET_ALL)
        except ValueError:
            print(Fore.RED + "Please enter a valid number!" + Style.RESET_ALL)

if __name__ == "__main__":
    try:
        bot = PRBot()
        bot.display_banner()
        bot.interactive_menu()
    except Exception as e:
        print(Fore.RED + f"Fatal error: {str(e)}" + Style.RESET_ALL)
    finally:
        if 'bot' in locals():
            bot.cleanup()
