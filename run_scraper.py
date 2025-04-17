#!/usr/bin/env python3
import argparse
from websiteParser import WebsiteTextExtractor, logger

def main():
    parser = argparse.ArgumentParser(description="Extract text from website and its subpages")
    parser.add_argument("--url", type=str, default="https://www.angelone.in/support",
                      help="Base URL to scrape (default: https://www.angelone.in/support)")
    parser.add_argument("--depth", type=int, default=5,
                      help="Maximum depth to crawl (default: 5)")
    parser.add_argument("--delay", type=float, default=0.5,
                      help="Delay between requests in seconds (default: 1.5)")
    parser.add_argument("--output", type=str, default="./data",
                      help="Output directory for data (default: ./data)")
    args = parser.parse_args()

    logger.info(f"Starting extraction from {args.url} with max depth {args.depth}")
    
    extractor = WebsiteTextExtractor(
        base_url=args.url,
        max_depth=args.depth,
        delay=args.delay,
        output_dir=args.output
    )
    
    all_text = extractor.extract_all_text()
    
    logger.info(f"Extraction complete. Processed {len(extractor.visited_urls)} URLs and extracted text from {len(all_text)} pages.")
    logger.info(f"Results saved to {args.output}")

if __name__ == "__main__":
    main() 