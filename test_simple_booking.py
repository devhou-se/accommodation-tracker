#!/usr/bin/env python3

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright

async def test_simple_booking():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Not headless to see what happens
        page = await browser.new_page()
        
        url = "https://www6.489pro.com/asp/489/menu.asp?id=21560019&lan=ENG&kid=00156"
        print(f"Navigating to: {url}")
        await page.goto(url)
        await page.wait_for_load_state('networkidle')
        
        # Look for the October package
        page_text = await page.content()
        if "Traditional Gassho style house(1 Night with 2 meals) ～2025（OCT～NOV)" in page_text:
            print("✓ Found October package")
        else:
            print("✗ October package not found")
        
        # Find all calendar tables
        tables = await page.query_selector_all('table')
        print(f"Found {len(tables)} tables")
        
        # Look for calendar table with room data
        october_table = None
        for i, table in enumerate(tables):
            table_text = await table.text_content()
            print(f"Table {i} sample: {table_text[:200]}")
            if 'tatami' in table_text.lower():
                print(f"Table {i} contains tatami (room) data")
                october_table = table
                break
        
        if october_table:
            # Check current calendar view
            calendar_text = await october_table.text_content()
            print(f"Current calendar sample: {calendar_text[:500]}")
            
            # Look for 10/10 directly
            if '10/10' in calendar_text:
                print("✓ Found 10/10 in calendar!")
                
                # Extract room availability for 10/10
                rows = await october_table.query_selector_all('tr')
                for row in rows:
                    row_text = await row.text_content()
                    if 'tatami' in row_text.lower():
                        cells = await row.query_selector_all('td, th')
                        print(f"Room row: {row_text[:100]}")
                        
                        # Find 10/10 column
                        for j, cell in enumerate(cells):
                            cell_text = await cell.text_content()
                            if '10/10' in cell_text:
                                print(f"10/10 is in column {j}")
                                # Check availability in this column for room rows
                                break
            else:
                print("✗ 10/10 not found in current view, need to navigate")
                
                # Try clicking Next multiple times to reach October
                for click_attempt in range(10):  # Try up to 10 times
                    next_buttons = await page.query_selector_all('a:has-text("Next")')
                    print(f"Attempt {click_attempt + 1}: Found {len(next_buttons)} Next buttons")
                    
                    if not next_buttons:
                        print("No more Next buttons found")
                        break
                    
                    clicked = False
                    for i, btn in enumerate(next_buttons):
                        if await btn.is_visible():
                            print(f"Clicking Next button {i}")
                            await btn.click()
                            clicked = True
                            break
                    
                    if not clicked:
                        print("No clickable Next buttons found")
                        break
                    
                    await page.wait_for_timeout(3000)  # Wait longer for AJAX
                    
                    # Re-find the table (it might have been replaced)
                    tables = await page.query_selector_all('table')
                    for table in tables:
                        table_text = await table.text_content()
                        if 'tatami' in table_text.lower():
                            october_table = table
                            break
                    
                    if october_table:
                        updated_calendar_text = await october_table.text_content()
                        print(f"Current view sample: {updated_calendar_text[:200]}")
                        
                        if '10/10' in updated_calendar_text:
                            print("✓ Found 10/10 after navigation!")
                            
                            # Extract availabilities for 10/10
                            rows = await october_table.query_selector_all('tr')
                            availability_count = 0
                            
                            for row in rows:
                                cells = await row.query_selector_all('td, th')
                                if len(cells) < 3:
                                    continue
                                
                                # Check if this is a room row
                                first_cell_text = await cells[0].text_content() if cells else ""
                                if 'tatami' in first_cell_text.lower():
                                    row_text = await row.text_content()
                                    
                                    # Find the column with 10/10
                                    for j, cell in enumerate(cells):
                                        cell_text = await cell.text_content()
                                        if '○' in cell_text and 'JPY' in cell_text and j > 2:  # Skip first few columns
                                            # Check if this column corresponds to 10/10
                                            header_row = rows[0] if rows else None
                                            if header_row:
                                                header_cells = await header_row.query_selector_all('td, th')
                                                if j < len(header_cells):
                                                    header_text = await header_cells[j].text_content()
                                                    if '10/10' in header_text or '10/10' in cell_text:
                                                        print(f"Found availability: {first_cell_text.strip()} - {cell_text}")
                                                        availability_count += 1
                            
                            print(f"Total availabilities found for 10/10: {availability_count}")
                            break
        else:
            print("✗ No October calendar table found")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_simple_booking())