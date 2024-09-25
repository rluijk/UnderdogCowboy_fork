import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse

def scrape_visible_text(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except requests.RequestException as e:
        return f"Failed to retrieve the webpage. Error: {str(e)}"

def save_to_file(content, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)

def process_urls(urls, save_path):
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    for url in urls:
        visible_text = scrape_visible_text(url)
        
        # Create a filename based on the URL
        parsed_url = urlparse(url)
        filename = parsed_url.netloc + parsed_url.path.replace('/', '_')
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        full_path = os.path.join(save_path, filename)
        save_to_file(visible_text, full_path)
        print(f"Content from {url} has been saved to {full_path}")

# Example usage with an absolute path
urls_to_scrape = [
    "https://textual.textualize.io/widgets/button/",
    "https://textual.textualize.io/widgets/checkbox/",
    "https://textual.textualize.io/widgets/input/"
]

# Using an absolute path (adjust this to your system)
save_directory = "/Users/reneluijk/llm_agent_inputs"

process_urls(urls_to_scrape, save_directory)