#!/usr/bin/env python3

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright

async def test_final_booking():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        url = "https://www6.489pro.com/asp/489/menu.asp?id=21560019&lan=ENG&kid=00156"
        print(f"Navigating to: {url}")
        await page.goto(url)
        await page.wait_for_load_state('networkidle')
        
        # Navigate to October 10, 2025
        found_target = False
        
        for attempt in range(15):
            # Check if 10/10 is visible
            page_text = await page.content()
            if '10/10' in page_text:
                print(f"✓ Found 10/10 after {attempt} navigation attempts!")
                found_target = True
                break
            
            # Click Next button
            next_buttons = await page.query_selector_all('a:has-text("Next")')
            if next_buttons:
                for btn in next_buttons:
                    if await btn.is_visible():
                        await btn.click()
                        break
                await page.wait_for_timeout(2000)
            else:
                break
        
        if found_target:
            # Extract availabilities for 10/10
            tables = await page.query_selector_all('table')
            availability_count = 0
            
            for table in tables:
                table_text = await table.text_content()
                if 'tatami' in table_text.lower() and '10/10' in table_text:
                    print(f"Processing table with 10/10 data...")
                    
                    rows = await table.query_selector_all('tr')
                    for row in rows:
                        row_text = await row.text_content()
                        
                        # Look for room rows with tatami and check for availability on 10/10
                        if 'tatami' in row_text.lower():
                            print(f"Room row: {row_text}")
                            
                            # Extract room type
                            room_match = re.search(r'(\d+\s*Japanese\s*Tatami\s*mats)', row_text, re.IGNORECASE)
                            if room_match:
                                room_type = room_match.group(1)
                                
                                # The availability data after "calendar" shows the status for each day
                                # We need to parse the sequence after "calendar" to find the 10/10 slot
                                calendar_pos = row_text.lower().find('calendar')
                                if calendar_pos != -1:
                                    availability_part = row_text[calendar_pos + 8:]  # After "calendar"
                                    
                                    # Parse the availability symbols in sequence
                                    # Based on our observation: ××○JPY17,050××××
                                    # This means: 10/8(×), 10/9(×), 10/10(○JPY17,050), 10/11(×), etc.
                                    
                                    # Find ○JPY pattern which indicates availability
                                    print(f"  Availability part: {availability_part}")
                                    
                                    # Better regex to capture the pattern
                                    symbols = re.findall(r'×|○(?:JPY[\d,]+)?', availability_part)
                                    print(f"  Availability symbols: {symbols}")
                                    
                                    # Position 2 (0-indexed) should be 10/10
                                    if len(symbols) > 2 and symbols[2].startswith('○'):
                                        # Extract price from the full symbol
                                        price_match = re.search(r'JPY([\d,]+)', symbols[2])
                                        if price_match:
                                            price = price_match.group(1)
                                            print(f"✓ AVAILABILITY FOUND: {room_type} - JPY{price} on 10/10")
                                            availability_count += 1
                                        else:
                                            # Look for price in the surrounding text
                                            price_in_text = re.search(r'○JPY([\d,]+)', availability_part)
                                            if price_in_text:
                                                price = price_in_text.group(1)
                                                print(f"✓ AVAILABILITY FOUND: {room_type} - JPY{price} on 10/10")
                                                availability_count += 1
            
            print(f"\n=== SUMMARY ===")
            print(f"Total availabilities found for 2025-10-10: {availability_count}")
            
            if availability_count == 2:
                print("✓ SUCCESS: Found expected 2 room types available (8 and 12 tatami)")
            else:
                print(f"✗ Expected 2 availabilities, found {availability_count}")
        else:
            print("✗ Could not navigate to 10/10")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_final_booking())