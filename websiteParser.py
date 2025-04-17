import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import List, Dict, Set, Optional, Tuple
import time
import os
import json
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class WebsiteTextExtractor:
    def __init__(self, base_url: str, max_depth: int = 5, delay: float = 1.0, output_dir: str = "./data"):
        """
        Initialize the website text extractor.
        
        Args:
            base_url: The starting URL to scrape (e.g., "https://www.angelone.in/support")
            max_depth: How many levels deep to follow links (default: 5)
            delay: Seconds to wait between requests (default: 1.0)
            output_dir: Directory to save extracted data (default: "./data")
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
        self.to_visit: List[Tuple[str, int]] = [(self.base_url, 0)]  # (url, depth)
        
        # Results storage
        self.results: Dict[str, str] = {}

        # Common elements to filter out (usually navigation, header, footer, etc.)
        self.elements_to_filter = [
            'header', 'footer', 'nav', '#header', '#footer', '#nav', 
            '.header', '.footer', '.nav', '.navigation', '.menu',
            '.sidebar', '.breadcrumb', '.banner', '.cookie-banner',
            '.social-links', '.copyright', '.announcement',
            '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
            '.navbar', '.site-header', '.site-footer', '.top-bar',
            '.search-form', '.download-app', '.mobile-nav',
            '.main-navigation', '#main-navigation', '#primaryNav',
            '.social-media', '.advertisement', '.ad-container',
            'aside', '.sidebar', '.popular-links', '.quick-links',
            '#sideNavigation', '.primary-nav',
            '[id*="header"]', '[id*="footer"]', '[id*="menu"]', 
            '[id*="navigation"]', '[id*="nav"]', '[class*="header"]',
            '[class*="footer"]', '[class*="menu"]', '[class*="navigation"]',
            '[class*="nav-"]', '[class*="-nav"]'
        ]
    
    def extract_all_text(self) -> Dict[str, str]:
        """
        Extract text from the base URL and all sub-URLs within the same path.
        
        Returns:
            Dictionary with URLs as keys and extracted text as values
        """
        # Use breadth-first search to crawl the website
        while self.to_visit:
            url, depth = self.to_visit.pop(0)
            
            if url in self.visited_urls or depth > self.max_depth:
                continue
                
            self._process_url(url, depth)
            
            # Save progress after each page
            self._save_progress()
            
        return self.results
    
    def _process_url(self, url: str, depth: int) -> None:
        """Process a single URL, extract text, and find links."""
        if url in self.visited_urls:
            return
            
        # Respect crawl delay
        time.sleep(self.delay)
        
        try:
            logger.info(f"Processing: {url} (depth: {depth})")
            response = requests.get(url, headers=self.headers, timeout=15)
            
            # Mark as visited even if there's an error
            self.visited_urls.add(url)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
                return
                
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower():
                logger.warning(f"Skipping non-HTML content at {url}: {content_type}")
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract and clean text
            text = self._extract_text_from_soup(soup)
            self.results[url] = text
            
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
    
    def _extract_text_from_soup(self, soup: BeautifulSoup) -> str:
        """
        Extract and clean text from BeautifulSoup object, focusing on main content
        and excluding navigation, headers, footers and other non-essential parts.
        """
        # Create a copy to work with
        soup_copy = BeautifulSoup(str(soup), 'html.parser')
        
        # Remove unwanted elements - first pass (standard elements)
        for element in soup_copy.select('script, style, meta, link, noscript, iframe, [style*="display:none"], [style*="display: none"]'):
            element.decompose()
        
        # Remove common navigation, header, footer elements - second pass
        for selector in self.elements_to_filter:
            for element in soup_copy.select(selector):
                element.decompose()
        
        # AngelOne-specific selectors (based on inspection of the site structure)
        angelone_selectors = [
            '.open-account-area', '.download-app-area', '.sip-calc-area',
            '.search-area', '.top-nav', '.main-nav', '.primary-nav',
            '.footer-top', '.footer-bottom', '.copyright-area',
            '.login-area', '.quick-links', '.popular-stocks',
            '.mobile-menu', '.mobile-nav', '.pricing-section',
            'nav', '[id*="menu"]', '[class*="menu"]',
            '.open-account-btn', '.login-btn', '.download-section',
            '.user-links', '.open-demat', '.quick-links',
            '.popular-links', '.attention-investors',
            '.open-free-demat-account', '.oda-footer',
            'form', '.social-links',
            # Additional AngelOne specific selectors for common elements
            '.we-are-here-to-help-you', '.quick-links-10', 
            '.connect-with-us', '.partnership-request', '.media-queries',
            '.en', '.hi'
        ]
        
        # Apply AngelOne-specific filtering
        for selector in angelone_selectors:
            for element in soup_copy.select(selector):
                element.decompose()
                
        # Try to identify the main content area
        # First, check for specific content identifiers (usually main article area)
        main_content = None
        
        # Look for specific AngelOne content containers
        for content_selector in ['.support-container', '.faq-container', '.support-content', 
                               '#support-content', '.article-content', '.content-area',
                               'main', 'article', '[role="main"]', '.faq-content']:
            main_content = soup_copy.select_one(content_selector)
            if main_content:
                break
        
        # If we couldn't find a specific content container, try a more generic approach
        if not main_content:
            main_content = soup_copy.find(attrs={'id': re.compile(r'(main|content|article|post)', re.I)})
        if not main_content:
            main_content = soup_copy.find(attrs={'class': re.compile(r'(main|content|article|post)', re.I)})
        
        # If we found a main content container, use it
        if main_content:
            # Extract only from main content
            soup_copy = BeautifulSoup(str(main_content), 'html.parser')
        else:
            # If we can't find a clear main content area, try to remove clearly non-content areas
            # like repetitive navigation links, and then use what's left
            for element in soup_copy.find_all(string=lambda text: text and any(nav_text in text.lower() for nav_text in 
                                       ['login', 'sign up', 'open account', 'download', 'download app', 
                                        'register', 'create account', 'quick links', 'we are here to help you',
                                        'connect with us', 'partnership request', 'media queries'])):
                parent = element.parent
                if parent:
                    parent.decompose()
            
            # Remove elements with very few words (likely navigation or button text)
            for element in soup_copy.find_all(['a', 'span', 'button']):
                text = element.get_text().strip()
                if text and len(text.split()) <= 3:
                    element.decompose()
            
            # Try to identify the main content based on text density
            # Content usually has the most text and paragraphs
            content_candidates = []
            for element in soup_copy.find_all(['div', 'section', 'article', 'main']):
                if element.find_all(['p', 'h2', 'h3', 'li']):
                    content_candidates.append((element, len(element.get_text())))
            
            # Sort by text length (descending) and use the one with most text
            if content_candidates:
                content_candidates.sort(key=lambda x: x[1], reverse=True)
                soup_copy = BeautifulSoup(str(content_candidates[0][0]), 'html.parser')
        
        # Extract title (prefer page-specific title over site title)
        title = ""
        if soup_copy.h1:
            title = soup_copy.h1.get_text().strip()
        elif soup_copy.title:
            title = soup_copy.title.get_text().strip()
            # Remove site name if present (usually after " - " or " | ")
            title = re.sub(r'\s*[\-\|]\s*.+$', '', title)
        
        # Remove "Quick Links" and common sections that appear on every page
        common_phrases = [
            "We are here to help you", "Quick Links", "Track Application Status",
            "Want to connect with us?", "Connect with us", "Partnership Request", 
            "Media Queries", "Our experts will be happy to assist you",
            "Still have any queries?", "Connect with our support team", 
            "For any partnership requests please reach us at", "EMAIL US",
            "partners@angelbroking.com", "Learn More", "Create Ticket",
            "022-40003600", "CONTACT US"
        ]
        
        for phrase in common_phrases:
            for element in soup_copy.find_all(string=lambda text: text and phrase in text):
                parent = element.parent
                if parent:
                    parent.decompose()
        
        # Extract headings from h2-h6 (h1 is usually handled as title)
        headings = []
        for h_tag in soup_copy.find_all(['h2', 'h3', 'h4', 'h5', 'h6']):
            # Skip empty headings or those that look like navigation/menu items
            heading_text = h_tag.get_text().strip()
            if heading_text and len(heading_text) > 1 and not any(nav_word in heading_text.lower() for nav_word in ['menu', 'navigation', 'login', 'download', 'open demat']):
                if not any(phrase in heading_text for phrase in common_phrases):
                    headings.append(heading_text)
        
        # Extract paragraphs and list items (main content)
        paragraphs = []
        for p_tag in soup_copy.find_all(['p', 'li', 'div.content', 'section']):
            # Skip empty elements or very short ones that are likely UI elements
            p_text = p_tag.get_text().strip()
            if p_text and len(p_text) > 5:  # Increased minimum length to filter out more noise
                # Skip elements that are likely navigation or other non-content elements
                if not any(nav_word in p_text.lower() for nav_word in ['login', 'signup', 'sign up', 'download', 'cookie', 'privacy', 'open demat', 'download app']):
                    # Skip text containing common phrases that appear on every page
                    if not any(phrase in p_text for phrase in common_phrases):
                        # Skip repetitive text that appears multiple times
                        if p_text not in paragraphs:
                            paragraphs.append(p_text)
        
        # Filter text based on word count (skip very short lines that are likely UI elements)
        filtered_paragraphs = []
        for p in paragraphs:
            # Skip very short lines unless they appear to be bullet points or important items
            if len(p.split()) > 3 or p.startswith('•') or p.startswith('-'):
                filtered_paragraphs.append(p)
                
        # If we have very few paragraphs but headings, it's likely we have a list of links
        # In this case, we'll keep the headings but add explanatory text
        if len(filtered_paragraphs) < 3 and headings:
            filtered_paragraphs.append("This page appears to be a navigation/category page with the following options:")
        
        # Combine all text with proper formatting
        all_text = []
        if title:
            all_text.append(f"# {title}")
            all_text.append("")
            
        if headings:
            all_text.extend(headings)
            all_text.append("")
            
        if filtered_paragraphs:
            all_text.extend(filtered_paragraphs)
        
        # Clean and normalize text
        text = "\n".join(all_text)
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove multiple blank lines
        text = re.sub(r' +', ' ', text)  # Normalize spaces
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)  # Convert single newlines to spaces
        
        # Final cleanup to remove duplicated content
        lines = text.split('\n')
        unique_lines = []
        seen_lines = set()
        
        for line in lines:
            line_lower = line.lower()
            # Skip empty lines or lines we've seen before
            if line and line_lower not in seen_lines:
                unique_lines.append(line)
                seen_lines.add(line_lower)
        
        return '\n'.join(unique_lines)
    
    def _save_progress(self) -> None:
        """Save current results to files."""
        # Save as JSON
        with open(self.output_dir / "website_data.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
            
        # Save as text file (all content combined)
        with open(self.output_dir / "website_text.txt", "w", encoding="utf-8") as f:
            for url, text in self.results.items():
                if text.strip():  # Only write non-empty content
                    f.write(f"URL: {url}\n")
                    f.write("=" * 80 + "\n")
                    f.write(text)
                    f.write("\n\n" + "=" * 80 + "\n\n")
                
        # Save URLs visited
        with open(self.output_dir / "visited_urls.txt", "w", encoding="utf-8") as f:
            for url in sorted(self.visited_urls):
                f.write(f"{url}\n")
                
        logger.info(f"Saved {len(self.results)} pages to {self.output_dir}")


# Example usage
if __name__ == "__main__":
    extractor = WebsiteTextExtractor(
        base_url="https://www.angelone.in/support",
        max_depth=5,     # Increase depth to reach more pages
        delay=1.5,       # Be polite with 1.5 seconds between requests
        output_dir="./data"
    )
    
    logger.info("Starting extraction...")
    all_text = extractor.extract_all_text()
    
    logger.info(f"Extraction complete. Processed {len(extractor.visited_urls)} URLs and extracted text from {len(all_text)} pages.")
    logger.info(f"Results saved to {extractor.output_dir}")