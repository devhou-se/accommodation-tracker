#!/usr/bin/env python3

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright

async def test_correct_booking():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        url = "https://www6.489pro.com/asp/489/menu.asp?id=21560019&lan=ENG&kid=00156"
        print(f"Navigating to: {url}")
        await page.goto(url)
        await page.wait_for_load_state('networkidle')
        
        # Find all calendar tables
        tables = await page.query_selector_all('table')
        print(f"Found {len(tables)} tables")
        
        # Look for the October calendar table specifically
        # The calendar table for October package should be the second one that contains tatami
        october_table = None
        tatami_tables = []
        
        for i, table in enumerate(tables):
            table_text = await table.text_content()
            if 'tatami' in table_text.lower():
                tatami_tables.append((i, table))
        
        print(f"Found {len(tatami_tables)} tables with tatami (room) data")
        
        # The October package table should be the second one, or we need to identify it by context
        if len(tatami_tables) >= 2:
            print("Checking second tatami table for October data...")
            october_table = tatami_tables[1][1]
        elif len(tatami_tables) == 1:
            print("Only one tatami table found, checking if it's the October one...")
            october_table = tatami_tables[0][1]
        
        if october_table:
            # Navigate to find 10/10 in the October table
            found_target = False
            
            for attempt in range(10):
                calendar_text = await october_table.text_content()
                print(f"Attempt {attempt + 1} - Calendar text sample: {calendar_text[:300]}")
                
                if '10/10' in calendar_text:
                    print("✓ Found 10/10!")
                    found_target = True
                    
                    # Extract availabilities
                    rows = await october_table.query_selector_all('tr')
                    print(f"Found {len(rows)} rows in calendar table")
                    
                    # Find header row to identify 10/10 column
                    header_row = None
                    target_column = None
                    
                    for i, row in enumerate(rows):
                        row_text = await row.text_content()
                        if '10/10' in row_text:
                            header_row = row
                            cells = await row.query_selector_all('td, th')
                            for j, cell in enumerate(cells):
                                cell_text = await cell.text_content()
                                if '10/10' in cell_text:
                                    target_column = j
                                    print(f"Found 10/10 in row {i}, column {j}")
                                    break
                            break
                    
                    if target_column is not None:
                        # Check availability in room rows
                        availability_count = 0
                        for i, row in enumerate(rows):
                            cells = await row.query_selector_all('td, th')
                            row_text = await row.text_content()
                            print(f"Row {i}: {row_text[:100]}")
                            
                            if len(cells) > target_column:
                                first_cell = cells[0] if cells else None
                                target_cell = cells[target_column]
                                
                                if first_cell:
                                    first_text = await first_cell.text_content()
                                    target_text = await target_cell.text_content()
                                    
                                    print(f"  First cell: '{first_text}', Target cell: '{target_text}'")
                                    
                                    if 'tatami' in first_text.lower() and '○' in target_text and 'JPY' in target_text:
                                        print(f"✓ Availability: {first_text.strip()} - {target_text.strip()}")
                                        availability_count += 1
                        
                        print(f"Total availabilities found for 10/10: {availability_count}")
                    break
                
                # Look for Next button specifically for this table/section
                next_buttons = await page.query_selector_all('a:has-text("Next")')
                
                if attempt == 0:
                    print(f"Found {len(next_buttons)} Next buttons total")
                
                # Try to click the relevant Next button
                clicked = False
                for btn in next_buttons:
                    if await btn.is_visible():
                        print(f"Clicking Next button")
                        await btn.click()
                        clicked = True
                        break
                
                if not clicked:
                    print("No more clickable Next buttons")
                    break
                
                await page.wait_for_timeout(3000)
                
                # Re-find the October table after navigation
                tables = await page.query_selector_all('table')
                tatami_tables = []
                for i, table in enumerate(tables):
                    table_text = await table.text_content()
                    if 'tatami' in table_text.lower():
                        tatami_tables.append((i, table))
                
                if len(tatami_tables) >= 2:
                    october_table = tatami_tables[1][1]
                elif len(tatami_tables) == 1:
                    october_table = tatami_tables[0][1]
            
            if not found_target:
                print("✗ Could not find 10/10 after navigation attempts")
        else:
            print("✗ No October calendar table found")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_correct_booking())