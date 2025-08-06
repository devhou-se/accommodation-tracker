#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers import ShirakawaScraper


async def quick_test():
    """Test the scraper with just one accommodation."""
    print("Quick test with one accommodation...")
    
    scraper = ShirakawaScraper(timeout_seconds=30)
    
    try:
        await scraper._initialize_browser()
        
        # Just test Rihee (which we know works)
        acc_info = {
            'name': 'Rihee', 
            'url': 'https://shirakawa-go.gr.jp/en/stay/33/'
        }
        
        target_dates = ["2025-08-27", "2025-08-28", "2025-08-31"]
        
        print(f"Testing {acc_info['name']} for dates: {target_dates}")
        
        result = await scraper._check_single_accommodation(acc_info, target_dates)
        
        if result:
            print("\n✅ SUCCESS! Found availability:")
            print(f"   Name: {result.accommodation_name}")
            print(f"   Available dates: {result.available_dates}")
            print(f"   Location: {result.location}")
            print(f"   Link: {result.link}")
        else:
            print("\n❌ No availability found for target dates")
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(quick_test())