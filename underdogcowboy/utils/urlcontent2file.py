import requests
import os
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def get_webpage_content(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    
    # Drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def save_content_to_file(content, url):
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    
    if not filename:
        filename = 'index'
    
    filename = f"{filename}.txt"
    
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"Content saved to {filename}")

# Main execution
if __name__ == "__main__":
    url = input("Enter the URL: ")
    html_content = get_webpage_content(url)
    
    if html_content:
        text_content = extract_text_from_html(html_content)
        save_content_to_file(text_content, url)