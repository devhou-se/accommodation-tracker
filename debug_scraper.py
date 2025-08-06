#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers import ShirakawaScraper


async def debug_accommodation_list():
    """Debug accommodation list extraction."""
    print("Debugging accommodation list...")
    
    scraper = ShirakawaScraper(timeout_seconds=30)
    
    try:
        await scraper._initialize_browser()
        accommodations = await scraper._get_accommodation_list()
        
        print(f"Found {len(accommodations)} accommodations:")
        for acc in accommodations:
            print(f"  - {acc['name']}: {acc['url']}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.cleanup()


async def debug_single_page():
    """Debug a single accommodation page."""
    print("Debugging single accommodation page...")
    
    scraper = ShirakawaScraper(timeout_seconds=30)
    
    try:
        await scraper._initialize_browser()
        
        # Test with a known URL
        test_url = "https://shirakawa-go.gr.jp/en/stay/33/"
        page = await scraper.context.new_page()
        
        await page.goto(test_url, timeout=30000)
        await page.wait_for_load_state('networkidle')
        
        # Look for reservation links
        print("Looking for reservation links...")
        
        # Try different selectors
        selectors_to_try = [
            'a:has-text("Click here for reservations")',
            'a[href*="489pro.com"]',
            'a[href*="menu.asp"]',
            'a:has-text("reservation")',
            'a:has-text("Click")'
        ]
        
        for selector in selectors_to_try:
            try:
                elements = await page.locator(selector).all()
                print(f"  {selector}: found {len(elements)} elements")
                if elements:
                    for i, element in enumerate(elements[:3]):  # Just first 3
                        href = await element.get_attribute('href')
                        text = await element.text_content()
                        print(f"    {i}: href={href}, text={text[:100] if text else None}")
            except Exception as e:
                print(f"  {selector}: error - {e}")
        
        # Let's also look for all links containing 489pro
        print("\nAll links containing 489pro:")
        all_links = await page.locator('a').all()
        for link in all_links:
            href = await link.get_attribute('href')
            if href and '489pro' in href:
                text = await link.text_content()
                print(f"  Found: {href} - '{text}'" )
                
        await page.close()
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    print("Choose test:")
    print("1. Debug accommodation list")
    print("2. Debug single page")
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(debug_accommodation_list())
    elif choice == "2":
        asyncio.run(debug_single_page())
    else:
        print("Invalid choice")