import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import List, Set
import time
import os
from pathlib import Path
import logging
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class WebsiteURLExtractor:
    def __init__(self, base_url: str, max_depth: int = 5, delay: float = 1.0, output_dir: str = "./data"):
        """
        Initialize the website URL extractor.
        
        Args:
            base_url: The starting URL to crawl (e.g., "https://www.angelone.in/support")
            max_depth: How many levels deep to follow links (default: 5)
            delay: Seconds to wait between requests (default: 1.0)
            output_dir: Directory to save extracted URLs (default: "./data")
        """
        self.base_url = base_url
        self.max_depth = max_depth
        self.delay = delay
        self.visited_urls: Set[str] = set()
        self.parsed_domain = urlparse(base_url)
        self.domain = self.parsed_domain.netloc
        self.base_path = self.parsed_domain.path
        
        # Ensure output directory exists
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure headers to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Track pages to visit
        self.to_visit: List = [(self.base_url, 0)]  # (url, depth)
        
        # Results storage
        self.extracted_urls: List[str] = []
    
    def extract_all_urls(self) -> List[str]:
        """
        Extract all URLs from the base URL and all sub-URLs within the same path.
        
        Returns:
            List of discovered URLs
        """
        # Use breadth-first search to crawl the website
        while self.to_visit:
            url, depth = self.to_visit.pop(0)
            
            if url in self.visited_urls or depth > self.max_depth:
                continue
                
            self._process_url(url, depth)
            
            # Save progress after every 10 URLs
            if len(self.extracted_urls) % 10 == 0:
                self._save_progress()
            
        # Final save
        self._save_progress()
        return self.extracted_urls
    
    def _process_url(self, url: str, depth: int) -> None:
        """Process a single URL and find links."""
        if url in self.visited_urls:
            return
            
        # Respect crawl delay
        time.sleep(self.delay)
        
        try:
            logger.info(f"Processing: {url} (depth: {depth})")
            response = requests.get(url, headers=self.headers, timeout=15)
            
            # Mark as visited even if there's an error
            self.visited_urls.add(url)
            
            # Add to extracted URLs if successful
            if response.status_code == 200:
                self.extracted_urls.append(url)
            else:
                logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
                return
                
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower():
                logger.warning(f"Skipping non-HTML content at {url}: {content_type}")
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links on the page
            self._find_links(soup, url, depth)
                
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
    
    def _find_links(self, soup: BeautifulSoup, current_url: str, current_depth: int) -> None:
        """Find all links on the page and add valid ones to the to_visit list."""
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip empty, javascript, and anchor links
            if not href or href.startswith('javascript:') or href.startswith('#'):
                continue
                
            # Build absolute URL
            next_url = urljoin(current_url, href)
            
            # Only process URLs that belong to our target domain and path
            if self._should_process_url(next_url):
                # Add to visit queue if not already visited
                if next_url not in self.visited_urls:
                    self.to_visit.append((next_url, current_depth + 1))
    
    def _should_process_url(self, url: str) -> bool:
        """Determine if a URL should be processed based on domain and path."""
        parsed = urlparse(url)
        
        # Must be same domain
        if parsed.netloc != self.domain:
            return False
            
        # Must start with the base path
        if not parsed.path.startswith(self.base_path):
            return False
            
        # Skip URLs with fragments or queries if the base URL is already visited
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if base_url in self.visited_urls and (parsed.fragment or parsed.query):
            return False
            
        return True
    
    def _save_progress(self) -> None:
        """Save discovered URLs to a file."""
        # Save the list of extracted URLs
        with open(self.output_dir / "extracted_urls.txt", "w", encoding="utf-8") as f:
            for url in self.extracted_urls:
                f.write(f"{url}\n")
        
        # Save visited URLs (including failed ones)
        with open(self.output_dir / "visited_urls.txt", "w", encoding="utf-8") as f:
            for url in sorted(self.visited_urls):
                f.write(f"{url}\n")
                
        logger.info(f"Saved {len(self.extracted_urls)} URLs to {self.output_dir / 'extracted_urls.txt'}")


def main():
    parser = argparse.ArgumentParser(description="Extract URLs from website and its subpages")
    parser.add_argument("--url", type=str, default="https://www.angelone.in/support",
                      help="Base URL to crawl (default: https://www.angelone.in/support)")
    parser.add_argument("--depth", type=int, default=5,
                      help="Maximum depth to crawl (default: 5)")
    parser.add_argument("--delay", type=float, default=1.5,
                      help="Delay between requests in seconds (default: 1.5)")
    parser.add_argument("--output", type=str, default="./data",
                      help="Output directory for data (default: ./data)")
    args = parser.parse_args()

    logger.info(f"Starting URL extraction from {args.url} with max depth {args.depth}")
    
    extractor = WebsiteURLExtractor(
        base_url=args.url,
        max_depth=args.depth,
        delay=args.delay,
        output_dir=args.output
    )
    
    all_urls = extractor.extract_all_urls()
    
    logger.info(f"Extraction complete. Processed {len(extractor.visited_urls)} URLs and extracted {len(all_urls)} valid URLs.")
    logger.info(f"Results saved to {args.output}/extracted_urls.txt")

if __name__ == "__main__":
    main() 