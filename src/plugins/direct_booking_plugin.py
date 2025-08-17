import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs

from playwright.async_api import async_playwright, Page, Browser
from .base import BookingPlugin, BookingAvailability, CheckResult


class DirectBookingPlugin(BookingPlugin):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("direct_booking", config)
        self.booking_urls = config.get('booking_urls', [])
        self.target_dates = [datetime.strptime(date, '%Y-%m-%d').date() for date in config.get('target_dates', [])]
        self.browser: Optional[Browser] = None
        self.logger = logging.getLogger(__name__)
        self.extracted_accommodation_names = []  # Store extracted names

    async def initialize(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)

    async def cleanup(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def check_availability(self) -> CheckResult:
        if not self.browser:
            await self.initialize()

        availabilities = []
        
        # Create tasks for checking all booking URLs and dates
        tasks = []
        for booking_url in self.booking_urls:
            for target_date in self.target_dates:
                tasks.append((booking_url, target_date))

        # Execute all checks in parallel using native async
        tasks_async = [
            self._check_single_booking(booking_url, target_date)
            for booking_url, target_date in tasks
        ]
        results = await asyncio.gather(*tasks_async, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Error checking availability: {result}")
            elif isinstance(result, list):
                availabilities.extend(result)

        # Convert to TicketAvailability objects
        ticket_availabilities = []
        for avail in availabilities:
            # Clean up the package name to just show the key info
            package_name = avail['package_name']
            if 'Traditional Gassho style house' in package_name:
                # Extract just the essential part
                if '～2025（OCT～NOV)' in package_name:
                    clean_package = "Oct-Nov 2025 Package"
                elif '～2025（JUL to SEP)' in package_name:
                    clean_package = "Jul-Sep 2025 Package"
                else:
                    clean_package = "Traditional Gassho Package"
            else:
                clean_package = package_name[:50] + "..." if len(package_name) > 50 else package_name
            
            booking_avail = BookingAvailability(
                date=avail['date'],
                room_type=f"{avail['room_type']} ({clean_package})",
                status=avail['status'],
                price=avail['price'],
                booking_url=avail['booking_url'],
                venue=avail['accommodation_name']
            )
            ticket_availabilities.append(booking_avail)

        # Use the first extracted accommodation name, or fallback to static name
        accommodation_name = self.extracted_accommodation_names[0] if self.extracted_accommodation_names else "Shirakawa-go Accommodation"
        
        return CheckResult(
            plugin_name=self.name,
            item_name=accommodation_name,
            check_time=datetime.now(timezone.utc),
            availabilities=ticket_availabilities,
            success=True
        )

    async def _check_single_booking(self, booking_url: str, target_date) -> List[Dict[str, Any]]:
        """Check availability for a single booking URL and date"""
        try:
            page = await self.browser.new_page()
            await page.goto(booking_url)
            await page.wait_for_load_state('networkidle')

            # Extract accommodation name from page
            accommodation_name = await self._extract_accommodation_name(page)
            # Store extracted accommodation name
            if accommodation_name and accommodation_name not in self.extracted_accommodation_names:
                self.extracted_accommodation_names.append(accommodation_name)
            
            # Find packages that match the target date
            matching_packages = await self._find_matching_packages(page, target_date)
            
            availabilities = []
            for package in matching_packages:
                # Navigate to the correct calendar week for our target date
                calendar_table = await self._navigate_to_target_date_calendar(page, package, target_date)
                
                if calendar_table:
                    # Extract room availability for the target date
                    room_availabilities = await self._extract_room_availability(
                        page, calendar_table, package, target_date, accommodation_name, booking_url
                    )
                    availabilities.extend(room_availabilities)

            await page.close()
            return availabilities

        except Exception as e:
            self.logger.error(f"Error checking {booking_url} for {target_date}: {e}")
            return []

    async def _extract_accommodation_name(self, page: Page) -> str:
        """Extract accommodation name from the page"""
        try:
            # Look for the main heading
            name_element = await page.query_selector('h1, .accommodation-name, [class*="title"]')
            if name_element:
                return await name_element.text_content()
            
            # Fallback to page title
            title = await page.title()
            if '|' in title:
                return title.split('|')[0].strip()
            
            return title.strip()
        except:
            return "Unknown Accommodation"

    async def _find_matching_packages(self, page: Page, target_date) -> List[Dict[str, Any]]:
        """Find packages that have date ranges covering the target date"""
        packages = []
        
        try:
            # For 489pro.com, look for the page structure with package titles and tables
            page_content = await page.content()
            
            # Look for package titles that contain date ranges and "Gassho"
            title_elements = await page.query_selector_all('*')
            
            for element in title_elements:
                try:
                    element_text = await element.text_content()
                    if not element_text:
                        continue
                    
                    # Look for Gassho style house packages with date ranges
                    if 'Traditional Gassho style house' in element_text and '(' in element_text:
                        # Extract the date range from the text
                        date_range_match = re.search(r'(\d{4}/\d{1,2}/\d{1,2})\s*-\s*(\d{4}/\d{1,2}/\d{1,2})', element_text)
                        
                        if date_range_match:
                            start_date_str = date_range_match.group(1)
                            end_date_str = date_range_match.group(2)
                            
                            # Parse dates
                            start_date = datetime.strptime(start_date_str, '%Y/%m/%d').date()
                            end_date = datetime.strptime(end_date_str, '%Y/%m/%d').date()
                            
                            # Check if target date falls within this package's date range
                            if start_date <= target_date <= end_date:
                                self.logger.info(f"Found matching package: {element_text.strip()}")
                                
                                # Find the next calendar table after this element
                                calendar_table = await self._find_calendar_table_for_package(element, page)
                                
                                packages.append({
                                    'title': element_text.strip(),
                                    'start_date': start_date,
                                    'end_date': end_date,
                                    'section': element,
                                    'calendar_table': calendar_table
                                })
                
                except Exception as e:
                    self.logger.debug(f"Error processing element: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error finding packages: {e}")

        return packages

    async def _find_calendar_table_for_package(self, package_section, page: Page):
        """Find the calendar table associated with a package section"""
        try:
            # For 489pro.com, the calendar table follows the package info
            # Look for all tables on the page and find the one with calendar structure
            all_tables = await page.query_selector_all('table')
            
            for table in all_tables:
                table_text = await table.text_content()
                # Look for calendar indicators
                if (any(indicator in table_text.lower() for indicator in ['room type', '○', '×', 'vacancy', 'tatami']) and
                    any(date_indicator in table_text for date_indicator in ['/', '(', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])):
                    self.logger.debug(f"Found calendar table with text sample: {table_text[:200]}")
                    return table
            
            self.logger.warning("No calendar table found")
            return None
            
        except Exception as e:
            self.logger.debug(f"Error finding calendar table: {e}")
            return None

    async def _navigate_to_target_date_calendar(self, page: Page, package: Dict, target_date) -> Optional[Any]:
        """Navigate to the calendar week containing the target date"""
        try:
            max_attempts = 15
            
            for attempt in range(max_attempts):
                # Check if target date is visible anywhere on the page
                page_content = await page.content()
                target_date_str = f"{target_date.month}/{target_date.day}"
                
                if target_date_str in page_content:
                    self.logger.info(f"Found target date {target_date} after {attempt} navigation attempts")
                    
                    # Find the calendar table that contains our target date
                    tables = await page.query_selector_all('table')
                    for table in tables:
                        table_text = await table.text_content()
                        if 'tatami' in table_text.lower() and target_date_str in table_text:
                            return table
                    
                    # If we found the date in the page but not in a table, return any calendar table
                    for table in tables:
                        table_text = await table.text_content()
                        if 'tatami' in table_text.lower():
                            return table
                
                # Try to click Next button to navigate
                next_buttons = await page.query_selector_all('a:has-text("Next")')
                clicked = False
                
                for btn in next_buttons:
                    if await btn.is_visible():
                        try:
                            await btn.click()
                            clicked = True
                            break
                        except Exception as e:
                            self.logger.debug(f"Failed to click Next button: {e}")
                            continue
                
                if not clicked:
                    self.logger.warning(f"No more clickable Next buttons after {attempt} attempts")
                    break
                
                # Wait for navigation to complete
                await page.wait_for_timeout(3000)

            self.logger.warning(f"Could not navigate to target date {target_date} after {max_attempts} attempts")
            
            # Return the best calendar table we can find
            tables = await page.query_selector_all('table')
            for table in tables:
                table_text = await table.text_content()
                if 'tatami' in table_text.lower():
                    return table
            
            return None

        except Exception as e:
            self.logger.error(f"Error navigating calendar: {e}")
            return None

    async def _extract_room_availability(self, page: Page, calendar_table, package: Dict, target_date, accommodation_name: str, booking_url: str) -> List[Dict[str, Any]]:
        """Extract room availability from the calendar table for the target date"""
        availabilities = []
        
        try:
            # For 489pro.com, the availability data is embedded in the row text, not in separate cells
            room_rows = await calendar_table.query_selector_all('tr')
            
            # First, determine which position in the week our target date is
            # Find the header row with dates
            target_position = None
            for row in room_rows:
                row_text = await row.text_content()
                if f"{target_date.month}/{target_date.day}" in row_text:
                    # Parse the header to find the position
                    date_matches = re.findall(r'(\d{1,2}/\d{1,2})', row_text)
                    target_date_str = f"{target_date.month}/{target_date.day}"
                    if target_date_str in date_matches:
                        target_position = date_matches.index(target_date_str)
                        self.logger.info(f"Found target date {target_date} at position {target_position}")
                        break

            if target_position is None:
                self.logger.warning(f"Could not find position of target date {target_date} in calendar")
                return availabilities

            # Now extract room availability for each room type
            for row in room_rows:
                try:
                    row_text = await row.text_content()
                    
                    # Skip non-room rows
                    if not ('tatami' in row_text.lower() and 'calendar' in row_text.lower()):
                        continue
                    
                    # Extract room type
                    room_match = re.search(r'(\d+\s*Japanese\s*Tatami\s*mats)', row_text, re.IGNORECASE)
                    if not room_match:
                        continue
                    
                    room_type = room_match.group(1).strip()
                    
                    # Find the availability data after "calendar"
                    calendar_pos = row_text.lower().find('calendar')
                    if calendar_pos == -1:
                        continue
                    
                    availability_part = row_text[calendar_pos + 8:]  # After "calendar"
                    
                    # Parse availability symbols in sequence
                    symbols = re.findall(r'×|○(?:JPY[\d,]+)?|-', availability_part)
                    
                    # Check if our target position has availability
                    if len(symbols) > target_position and symbols[target_position].startswith('○'):
                        # Extract price from the symbol
                        price_match = re.search(r'JPY([\d,]+)', symbols[target_position])
                        if price_match:
                            price = price_match.group(1)
                            
                            availability = {
                                'accommodation_name': accommodation_name,
                                'package_name': package['title'],
                                'room_type': room_type,
                                'date': target_date.strftime('%Y-%m-%d'),
                                'price': f"JPY{price}",
                                'status': 'available',
                                'booking_url': booking_url,
                                'last_checked': datetime.now(timezone.utc).isoformat()
                            }
                            
                            availabilities.append(availability)
                            self.logger.info(f"Found availability: {accommodation_name} - {room_type} - {target_date} - JPY{price}")

                except Exception as e:
                    self.logger.debug(f"Error processing room row: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting room availability: {e}")

        return availabilities

    def get_item_info(self) -> Dict:
        """Get basic accommodation information"""
        # Use extracted accommodation names if available, otherwise fallback to static name
        accommodation_name = ", ".join(self.extracted_accommodation_names) if self.extracted_accommodation_names else "Shirakawa-go Accommodation"
        venues = self.extracted_accommodation_names if self.extracted_accommodation_names else [f"URL {i+1}" for i in range(len(self.booking_urls))]
        
        return {
            "name": accommodation_name,
            "dates": [date.strftime('%Y-%m-%d') for date in self.target_dates],
            "venues": venues
        }

    def get_plugin_info(self) -> Dict[str, Any]:
        return {
            "name": "Direct Booking Plugin",
            "version": "1.0.0",
            "description": "Checks availability directly from booking URLs using Playwright",
            "supported_sites": ["489pro.com"]
        }