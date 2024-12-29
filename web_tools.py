from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from termcolor import colored
from langchain.tools import Tool
import time
import csv
import os

class WebTools:
    def __init__(self):
        print(colored("Setting up Chrome WebDriver...", "cyan"))
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print(colored("Chrome WebDriver initialized successfully", "green"))
            
        except Exception as e:
            print(colored(f"Error initializing Chrome WebDriver: {str(e)}", "red"))
            raise
            
        self.tools = [
            Tool(
                name="search_urls",
                func=self.search_urls,
                description="Searches the web for URLs related to a query"
            ),
            Tool(
                name="get_website_content",
                func=self.get_website_content,
                description="Searches website content for relevant information"
            ),
            Tool(
                name="extract_contact_info",
                func=self.extract_contact_info,
                description="Extracts contact information from the website"
            ),
            Tool(
                name="save_to_csv_file",
                func=self.save_to_csv_file,
                description="Saves the compiled lead data to a CSV file"
            )
        ]
        
    def search_urls(self, query):
        """Search for URLs related to the query"""
        try:
            print(colored(f"Searching for: {query}", "yellow"))
            
            # Use real web search
            self.driver.get(f"https://www.google.com/search?q={query}")
            time.sleep(2)  # Allow time for results to load
            
            # Extract search results
            results = []
            elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
            
            for element in elements[:5]:  # Get first 5 results
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, "h3")
                    link_elem = element.find_element(By.CSS_SELECTOR, "a")
                    snippet_elem = element.find_element(By.CSS_SELECTOR, "div.VwiC3b")
                    
                    result = {
                        "url": link_elem.get_attribute("href"),
                        "title": title_elem.text,
                        "snippet": snippet_elem.text
                    }
                    
                    # Filter out unwanted results
                    if any(x in result["url"].lower() for x in ["linkedin", "facebook", "twitter", "instagram", "youtube"]):
                        continue
                        
                    results.append(result)
                except Exception as e:
                    print(colored(f"Error extracting result: {str(e)}", "red"))
                    continue
            
            print(colored(f"Found {len(results)} agency websites", "green"))
            return results
            
        except Exception as e:
            print(colored(f"Error searching URLs: {str(e)}", "red"))
            return []
            
    def get_website_content(self, url):
        """Get relevant content from a website"""
        try:
            print(colored(f"Analyzing content for: {url}", "yellow"))
            print(colored(f"Loading URL: {url}", "cyan"))
            
            self.driver.get(url)
            time.sleep(2)  # Allow time for dynamic content to load
            
            # Extract text content
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            # Extract basic information
            content = {
                "about": "",
                "services": "",
                "clients": "",
                "has_ai_mention": False,
                "has_enterprise": False
            }
            
            # Look for about section
            about_elements = self.driver.find_elements(By.CSS_SELECTOR, "section#about, div#about, section.about, div.about")
            if about_elements:
                content["about"] = about_elements[0].text
                
            # Look for services section
            services_elements = self.driver.find_elements(By.CSS_SELECTOR, "section#services, div#services, section.services, div.services")
            if services_elements:
                content["services"] = services_elements[0].text
                
            # Look for client section
            client_elements = self.driver.find_elements(By.CSS_SELECTOR, "section#clients, div#clients, section.clients, div.clients")
            if client_elements:
                content["clients"] = client_elements[0].text
                
            # Check for AI mentions
            ai_keywords = ["artificial intelligence", "ai", "machine learning", "ml", "deep learning", "automation"]
            content["has_ai_mention"] = any(keyword in body_text for keyword in ai_keywords)
            
            # Check for enterprise focus
            enterprise_keywords = ["enterprise", "corporate", "fortune 500", "large business", "multinational"]
            content["has_enterprise"] = any(keyword in body_text for keyword in enterprise_keywords)
            
            return content
            
        except Exception as e:
            print(colored(f"Error getting website content: {str(e)}", "red"))
            return None
            
    def extract_contact_info(self, url):
        """Extract contact information from the website"""
        try:
            print(colored(f"Extracting contact info from: {url}", "yellow"))
            
            contact_info = {
                "emails": [],
                "phones": [],
                "linkedin_profiles": [],
                "instagram_profiles": [],
                "physical_addresses": []
            }
            
            # First try to find contact page link from homepage
            print(colored(f"Loading homepage: {url}", "cyan"))
            self.driver.get(url)
            time.sleep(2)
            
            # Extract social media links from homepage first
            # Look for links containing social media URLs, regardless of their text content
            social_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="linkedin.com"], a[href*="instagram.com"]')
            for link in social_links:
                href = link.get_attribute("href")
                if href:
                    if "linkedin.com" in href:
                        contact_info["linkedin_profiles"].append(href)
                    elif "instagram.com" in href:
                        contact_info["instagram_profiles"].append(href)
            
            # Also look for social media links in the footer specifically
            footer_elements = self.driver.find_elements(By.CSS_SELECTOR, 'footer, .footer, [class*="footer"]')
            for footer in footer_elements:
                social_links = footer.find_elements(By.CSS_SELECTOR, 'a[href*="linkedin.com"], a[href*="instagram.com"]')
                for link in social_links:
                    href = link.get_attribute("href")
                    if href:
                        if "linkedin.com" in href:
                            contact_info["linkedin_profiles"].append(href)
                        elif "instagram.com" in href:
                            contact_info["instagram_profiles"].append(href)
            
            # Look for contact page links with various common texts
            contact_link = None
            contact_texts = [
                "contact", "contact us", "get in touch", "say hi", "reach out",
                "talk to us", "connect", "let's talk", "write to us"
            ]
            
            # Try finding link by text
            for text in contact_texts:
                try:
                    # Try exact text
                    elements = self.driver.find_elements(By.XPATH, f"//a[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{text}']")
                    if elements:
                        contact_link = elements[0].get_attribute("href")
                        break
                        
                    # Try contains text
                    elements = self.driver.find_elements(By.XPATH, f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]")
                    if elements:
                        contact_link = elements[0].get_attribute("href")
                        break
                except:
                    continue
            
            # If no link found by text, try common URLs
            if not contact_link:
                contact_urls = [
                    f"{url}/contact",
                    f"{url}/contact-us",
                    f"{url}/get-in-touch",
                    f"{url}/connect",
                    f"{url}/about",
                    f"{url}/about-us"
                ]
            else:
                contact_urls = [contact_link]
                
            for contact_url in contact_urls:
                try:
                    print(colored(f"Loading contact page: {contact_url}", "cyan"))
                    self.driver.get(contact_url)
                    time.sleep(2)
                    
                    # Get page content
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    page_html = self.driver.page_source
                    
                    # Extract emails using common patterns
                    import re
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    found_emails = re.findall(email_pattern, page_text)
                    contact_info["emails"].extend([e for e in found_emails if not any(x in e.lower() for x in ["example", "domain", "email"])])
                    
                    # Extract phone numbers (UK format)
                    phone_pattern = r'(?:\+44|0)(?:[\s-]*\d){9,10}'
                    found_phones = re.findall(phone_pattern, page_text)
                    contact_info["phones"].extend(found_phones)
                    
                    # Extract social media profiles from contact page
                    social_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="linkedin.com"], a[href*="instagram.com"]')
                    for elem in social_elements:
                        href = elem.get_attribute("href")
                        if href:
                            if "linkedin.com" in href:
                                contact_info["linkedin_profiles"].append(href)
                            elif "instagram.com" in href:
                                contact_info["instagram_profiles"].append(href)
                    
                    # Extract physical address
                    # Look for common address containers
                    address_elements = self.driver.find_elements(
                        By.XPATH,
                        "//*[contains(@class, 'address') or contains(@class, 'location') or contains(@class, 'contact-details')]"
                    )
                    
                    if not address_elements:
                        # Try finding paragraphs containing postal code patterns
                        uk_postcode_pattern = r'[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}'
                        paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
                        for p in paragraphs:
                            text = p.text
                            if re.search(uk_postcode_pattern, text):
                                address_elements.append(p)
                    
                    for elem in address_elements:
                        addr_text = elem.text.strip()
                        if addr_text and len(addr_text) > 10:  # Basic validation to avoid too short strings
                            contact_info["physical_addresses"].append(addr_text)
                            
                except Exception as e:
                    print(colored(f"Error loading {contact_url}: {str(e)}", "red"))
                    continue
            
            # Remove duplicates while preserving order
            for key in contact_info:
                contact_info[key] = list(dict.fromkeys(contact_info[key]))
            
            return contact_info
            
        except Exception as e:
            print(colored(f"Error extracting contact info: {str(e)}", "red"))
            return None
            
    def save_to_csv_file(self, data, output_file):
        """Save lead data to CSV file"""
        try:
            print(colored(f"Saving data to: {output_file}", "cyan"))
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Define fieldnames based on expected data structure
            fieldnames = [
                "Search Query",
                "Company Name",
                "URL", 
                "Primary Services",
                "AI Mentions",
                "Decision Makers",
                "Email",
                "Phone",
                "LinkedIn",
                "Instagram",
                "Physical Address",
                "AI Interest Score",
                "Qualification Notes"
            ]
            
            # Extract search query from the output file name
            filename = os.path.basename(output_file)
            # Get everything before _leads_ and replace underscores with spaces
            search_query = filename.split('_leads_')[0]
            # Handle multi-word queries by replacing underscores with spaces
            search_query = ' '.join(word for word in search_query.split('_') if word)
            print(colored(f"Using search query: {search_query}", "cyan"))
            
            # Convert single dictionary to list if necessary
            if isinstance(data, dict):
                data = [data]
            elif isinstance(data, str):
                # Try to parse string as JSON
                import json
                try:
                    parsed_data = json.loads(data)
                    if isinstance(parsed_data, dict):
                        data = [parsed_data]
                    else:
                        data = parsed_data
                except json.JSONDecodeError:
                    # If not JSON, try to parse the markdown-like format
                    parsed_data = {}
                    current_key = None
                    for line in data.split("\n"):
                        line = line.strip()
                        if line.startswith("- **") and "**:" in line:
                            parts = line.split("**:")
                            key = parts[0].replace("- **", "").strip()
                            value = parts[1].strip()
                            parsed_data[key] = value
                    if parsed_data:
                        data = [parsed_data]
                    else:
                        raise ValueError("Data must be a dictionary, list of dictionaries, valid JSON string, or properly formatted markdown")
            elif not isinstance(data, list):
                raise ValueError("Data must be a dictionary or list of dictionaries")
            
            # Write data to CSV
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in data:
                    row_data = dict(row)  # Create a copy of the row
                    # Ensure search query is included and matches the filename
                    if "Search Query" not in row_data or not row_data["Search Query"]:
                        row_data["Search Query"] = search_query
                    writer.writerow(row_data)
                
            print(colored("Data saved successfully", "green"))
            return True
            
        except Exception as e:
            error_msg = f"Error saving to CSV: {str(e)}"
            print(colored(error_msg, "red"))
            raise ValueError(error_msg)
            
    def cleanup(self):
        """Clean up resources"""
        try:
            print(colored("Closing Chrome WebDriver...", "cyan"))
            if hasattr(self, 'driver'):
                self.driver.quit()
        except Exception as e:
            print(colored(f"Error during cleanup: {str(e)}", "red")) 