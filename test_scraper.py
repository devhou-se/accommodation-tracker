#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers import ShirakawaScraper


async def test_scraper():
    """Test the Shirakawa scraper with a few target dates."""
    print("Testing Shirakawa scraper...")
    
    scraper = ShirakawaScraper(timeout_seconds=30)
    target_dates = ["2025-08-27", "2025-08-28", "2025-08-31", "2025-09-02", "2025-09-03", "2025-09-04"]
    
    try:
        results = await scraper.check_availability(target_dates)
        
        print(f"\nFound {len(results)} results:")
        for result in results:
            print(f"- {result.accommodation_name}")
            print(f"  Location: {result.location}")
            print(f"  Available dates: {result.available_dates}")
            print(f"  Link: {result.link}")
            print(f"  Discovered at: {result.discovered_at}")
            print()
        
        if not results:
            print("No availability found for the target dates.")
            
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(test_scraper())