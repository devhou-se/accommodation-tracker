import re
import requests
import asyncio
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from .base import TicketPlugin, TicketAvailability, CheckResult

# Try to import playwright for dynamic content loading
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not available. Dynamic booking pages may not work properly.")


class ShirakawaAccommodationPlugin(TicketPlugin):
    """Plugin for checking Shirakawa-go accommodation availability"""
    
    def __init__(self, config: Dict):
        super().__init__("shirakawa_accommodation", config)
        self.base_url = config.get("url", "https://shirakawa-go.gr.jp")
        self.root_page = config.get("root_page", "https://shirakawa-go.gr.jp/en/stay/?tag%5B%5D=1&category%5B%5D=3#refine")
        self.target_dates = config.get("target_dates", [])  # List of dates in YYYY-MM-DD format
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.accommodation_log = []  # Track all accommodation details for debugging
    
    async def check_availability(self) -> CheckResult:
        """Check accommodation availability for target dates"""
        try:
            # Step 1: Get all accommodations from root page
            accommodations = self._get_all_accommodations()
            
            print(f"Checking all {len(accommodations)} accommodations")
            
            # Step 2-6: Check availability for each accommodation and each target date in parallel
            tasks = []
            for accommodation in accommodations:
                for target_date in self.target_dates:
                    tasks.append((accommodation, target_date))
            
            print(f"Running {len(tasks)} availability checks in parallel")
            
            # Execute all checks in parallel using native async
            tasks_async = [
                self._check_accommodation_availability(accommodation, target_date)
                for accommodation, target_date in tasks
            ]
            results = await asyncio.gather(*tasks_async, return_exceptions=True)
            
            # Filter out exceptions and flatten list results (since each check can return multiple room types)
            all_availabilities = []
            for result in results:
                if isinstance(result, list):
                    # Each accommodation check now returns a list of TicketAvailability objects
                    all_availabilities.extend(result)
                elif isinstance(result, TicketAvailability):
                    # Backward compatibility for single results
                    all_availabilities.append(result)
                elif isinstance(result, Exception):
                    print(f"Error in parallel check: {result}")
            
            # Write accommodation log to file for debugging
            self._write_accommodation_log()
            
            return CheckResult(
                plugin_name=self.name,
                event_name="Shirakawa-go Accommodation",
                check_time=datetime.now(timezone.utc),
                availabilities=all_availabilities,
                success=True
            )
            
        except Exception as e:
            # Still write log even on failure
            self._write_accommodation_log()
            return CheckResult(
                plugin_name=self.name,
                event_name="Shirakawa-go Accommodation",
                check_time=datetime.now(timezone.utc),
                availabilities=[],
                success=False,
                error_message=str(e)
            )
    
    def _get_all_accommodations(self) -> List[Dict]:
        """Step 1: Get all accommodation links from all pages"""
        all_accommodations = []
        page_num = 1
        max_pages = 5  # Safety limit
        
        try:
            while page_num <= max_pages:
                # Construct page URL
                if page_num == 1:
                    page_url = self.root_page
                else:
                    # Add page parameter to URL
                    base_url = self.root_page.split('#')[0]  # Remove fragment
                    separator = '&' if '?' in base_url else '?'
                    page_url = f"{base_url}{separator}page={page_num}"
                
                print(f"Checking page {page_num}: {page_url}")
                
                response = self.session.get(page_url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find accommodation listings - look for div.item elements
                item_divs = soup.find_all('div', class_='item')
                page_accommodations = []
                
                for item in item_divs:
                    # Find the link within the item
                    link = item.find('a')
                    if not link:
                        continue
                    
                    href = link.get('href')
                    if not href:
                        continue
                    
                    # Convert relative URL to absolute
                    if href.startswith('./'):
                        # Handle relative paths like ./4/ or ./29/
                        href = href[2:]  # Remove ./
                        href = urljoin(page_url, href)
                    elif not href.startswith('http'):
                        href = urljoin(self.base_url, href)
                    
                    # Extract accommodation name from h5 element
                    name_element = item.find('h5')
                    if name_element:
                        span = name_element.find('span', class_='txt')
                        name = span.get_text(strip=True) if span else name_element.get_text(strip=True)
                    else:
                        # Fallback to alt text from image
                        img = item.find('img')
                        name = img.get('alt', 'Unknown') if img else 'Unknown'
                    
                    # Extract category/type
                    category_element = item.find('span', class_='cate_s')
                    category = category_element.get_text(strip=True) if category_element else 'Accommodation'
                    
                    accommodation = {
                        'name': name,
                        'url': href,
                        'id': self._extract_accommodation_id(href),
                        'category': category
                    }
                    page_accommodations.append(accommodation)
                
                print(f"  Found {len(page_accommodations)} accommodations on page {page_num}")
                
                # If no accommodations found on this page, we've reached the end
                if not page_accommodations:
                    print(f"  No accommodations found on page {page_num}, stopping pagination")
                    break
                
                all_accommodations.extend(page_accommodations)
                
                # Check if there's a next page link
                pager = soup.find('div', class_='tmp_pager')
                if pager:
                    next_link = pager.find('li', class_='next')
                    if not next_link:
                        print(f"  No next page link found, stopping at page {page_num}")
                        break
                else:
                    print(f"  No pagination found, stopping at page {page_num}")
                    break
                
                page_num += 1
            
            print(f"Total found: {len(all_accommodations)} accommodations across {page_num} pages")
            for i, acc in enumerate(all_accommodations[:5]):  # Show first 5 for debugging
                print(f"  {i+1}. {acc['name']} ({acc['id']}): {acc['url']}")
            
            return all_accommodations
            
        except Exception as e:
            print(f"Error getting accommodations: {e}")
            return []
    
    def _extract_accommodation_id(self, url: str) -> str:
        """Extract accommodation ID from URL"""
        # Extract ID from URL like /en/stay/34/
        match = re.search(r'/stay/(\d+)/?', url)
        return match.group(1) if match else "unknown"
    
    async def _check_accommodation_availability(self, accommodation: Dict, target_date: str) -> List[TicketAvailability]:
        """Steps 2-6: Check availability for a specific accommodation and date - returns list for multiple room types"""
        
        # Log accommodation details for debugging
        accom_log_entry = {
            "name": accommodation['name'],
            "id": accommodation['id'],
            "url": accommodation['url'],
            "category": accommodation['category'],
            "target_date": target_date,
            "step": "start",
            "reservation_url": None,
            "error": None,
            "room_types_found": 0,
            "final_status": None
        }
        
        try:
            # Step 2-3: Get accommodation page and find reservation link
            print(f"    Getting reservation URL for {accommodation['name']} (ID: {accommodation['id']})")
            accom_log_entry["step"] = "getting_reservation_url"
            
            reservation_url = self._get_reservation_url(accommodation['url'])
            accom_log_entry["reservation_url"] = reservation_url
            
            if not reservation_url:
                print(f"    No reservation link found for {accommodation['name']} (ID: {accommodation['id']})")
                accom_log_entry["step"] = "no_reservation_link"
                accom_log_entry["final_status"] = "no_booking_system"
                self.accommodation_log.append(accom_log_entry)
                
                return [TicketAvailability(
                    date=target_date,
                    seat_type=accommodation['name'],
                    status="no_booking_system",
                    price="No online reservation system",
                    venue=f"Shirakawa-go ({accommodation['category']})",
                    booking_url=accommodation['url']
                )]
            
            print(f"    Found reservation URL: {reservation_url}")
            accom_log_entry["step"] = "checking_room_types"
            
            # Step 4-6: Check availability on booking page and get all room types
            print(f"    Checking all room types for {target_date}")
            room_availabilities = await self._check_all_room_types_availability(reservation_url, target_date)
            accom_log_entry["room_types_found"] = len(room_availabilities) if room_availabilities else 0
            
            # Create results for each room type found
            results = []
            if room_availabilities:
                print(f"    Found {len(room_availabilities)} room types")
                accom_log_entry["final_status"] = "multiple_room_types"
                for room_info in room_availabilities:
                    print(f"      {room_info['room_type']}: {room_info['status']}")
                    results.append(TicketAvailability(
                        date=target_date,
                        seat_type=f"{accommodation['name']} - {room_info['room_type']}",
                        status=room_info['status'],
                        booking_url=reservation_url if room_info['status'] == 'available' else accommodation['url'],
                        venue=f"Shirakawa-go ({accommodation['category']})",
                        price=room_info.get('price', f"ID: {accommodation['id']}")
                    ))
            else:
                # Fallback to single result if no room types detected
                print(f"    No room types detected, using fallback method")
                accom_log_entry["step"] = "fallback_method"
                is_available = self._check_date_availability(reservation_url, target_date)
                status = "available" if is_available else "not_available"
                print(f"    Result: {status}")
                accom_log_entry["final_status"] = status
                
                results.append(TicketAvailability(
                    date=target_date,
                    seat_type=accommodation['name'],
                    status=status,
                    booking_url=reservation_url if is_available else accommodation['url'],
                    venue=f"Shirakawa-go ({accommodation['category']})",
                    price=f"ID: {accommodation['id']}"
                ))
            
            accom_log_entry["step"] = "completed"
            self.accommodation_log.append(accom_log_entry)
            return results
            
        except Exception as e:
            error_msg = str(e)[:200]  # More detailed error message
            print(f"    Error checking {accommodation['name']} (ID: {accommodation['id']}): {error_msg}")
            accom_log_entry["step"] = "error"
            accom_log_entry["error"] = error_msg
            accom_log_entry["final_status"] = "error"
            self.accommodation_log.append(accom_log_entry)
            
            return [TicketAvailability(
                date=target_date,
                seat_type=accommodation['name'],
                status="error",
                price=f"Error: {error_msg[:50]}...",
                booking_url=accommodation['url']
            )]
    
    
    def _get_reservation_url(self, accommodation_url: str) -> Optional[str]:
        """Step 3-4: Get reservation URL from accommodation page"""
        try:
            response = self.session.get(accommodation_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for "Click here for reservations" link
            reservation_links = soup.find_all('a', string=lambda text: text and 'reservation' in text.lower())
            
            # Also look for links containing 489pro.com (the booking system)
            if not reservation_links:
                reservation_links = soup.find_all('a', href=lambda x: x and '489pro.com' in x)
            
            # Look for buttons with reservation text
            if not reservation_links:
                button_links = soup.find_all('a', class_=lambda x: x and 'btn' in ' '.join(x))
                for link in button_links:
                    text = link.get_text(strip=True).lower()
                    if 'reservation' in text or 'book' in text or 'click here' in text:
                        reservation_links.append(link)
            
            # Debug: Log what links we found
            all_links = soup.find_all('a', href=True)
            print(f"      Found {len(all_links)} total links on page")
            print(f"      Found {len(reservation_links)} reservation-related links")
            
            if reservation_links:
                href = reservation_links[0].get('href')
                if href:
                    final_url = href if href.startswith('http') else urljoin(self.base_url, href)
                    print(f"      Selected reservation URL: {final_url}")
                    return final_url
            
            # Log some sample links for debugging
            print(f"      Sample links found:")
            for link in all_links[:5]:  # Show first 5 links
                href = link.get('href', 'No href')
                text = link.get_text(strip=True)[:50]  # First 50 chars
                print(f"        - {text}: {href}")
            
            return None
            
        except Exception as e:
            print(f"Error getting reservation URL from {accommodation_url}: {e}")
            return None
    
    def _check_date_availability(self, reservation_url: str, target_date: str) -> bool:
        """Step 5-6: Check if target date is available on booking page"""
        try:
            # Parse target date
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            
            # Get the booking page
            response = self.session.get(reservation_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for calendar or date availability indicators
            availability = self._parse_calendar_availability(soup, target_dt)
            
            # If we can't find the target month, try navigating to it
            if availability is None:
                availability = self._navigate_to_target_month(reservation_url, target_dt)
            
            return availability if availability is not None else False
            
        except Exception as e:
            print(f"Error checking date availability: {e}")
            return False
    
    async def _check_all_room_types_availability(self, reservation_url: str, target_date: str) -> List[Dict]:
        """Check availability for all room types/packages on booking page using Playwright for dynamic content"""
        try:
            # Parse target date
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            
            # Use Playwright if available for dynamic content, otherwise fallback to requests
            if PLAYWRIGHT_AVAILABLE:
                print(f"      Using Playwright to fetch dynamic content from {reservation_url}")
                soup = await self._fetch_dynamic_page(reservation_url)
            else:
                print(f"      Using requests (Playwright not available) for {reservation_url}")
                # Fallback to requests (will miss dynamic content)
                response = self.session.get(reservation_url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            
            if not soup:
                return []
            
            # Find all room type/package sections
            room_types = self._extract_room_types_from_page(soup)
            
            if not room_types:
                # No room types detected, return empty list to trigger fallback
                return []
            
            # Check availability for each room type
            room_availabilities = []
            for room_type in room_types:
                availability = self._check_room_type_availability(soup, room_type, target_dt)
                room_availabilities.append({
                    'room_type': room_type['name'],
                    'status': availability['status'],
                    'price': availability.get('price', 'Price not available')
                })
            
            return room_availabilities
            
        except Exception as e:
            print(f"Error checking room types: {e}")
            return []
    
    def _extract_room_types_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract different room types/packages from booking page based on Playwright analysis"""
        try:
            room_types = []
            
            # Find all package sections - look for specific package titles
            package_elements = soup.find_all('div')
            
            # Find packages by looking for the exact pattern we saw in Playwright
            packages_found = []
            for div in package_elements:
                text = div.get_text(strip=True)
                
                # Look for the exact package names we found in Playwright
                if ('Traditional Gassho' in text and 
                    '(1 Night with 2 meals)' in text and 
                    ('★' in text or '☆' in text)):
                    
                    # Clean the package name
                    package_name = self._clean_package_name(text)
                    if package_name and len(package_name) < 200:  # Reasonable length
                        
                        # Find the corresponding calendar table for this package
                        calendar_table = self._find_package_calendar_table(div, soup)
                        if calendar_table:
                            packages_found.append({
                                'name': package_name,
                                'element': div,
                                'calendar_table': calendar_table
                            })
                            print(f"    Found package: {package_name}")
            
            # For each package, extract room types from its calendar table
            for package in packages_found:
                room_types_in_package = self._extract_room_types_from_calendar_table(
                    package['calendar_table'], package['name']
                )
                room_types.extend(room_types_in_package)
            
            print(f"    Extracted {len(room_types)} total room type/package combinations")
            for i, room_type in enumerate(room_types):
                print(f"      {i+1}. {room_type['name'][:80]}...")
            
            return room_types
            
        except Exception as e:
            print(f"Error extracting room types: {e}")
            return []
    
    def _find_package_calendar_table(self, package_div, soup: BeautifulSoup):
        """Find the calendar table associated with a package"""
        try:
            # Look for calendar tables near this package div
            # First, try to find a table within the same parent container
            parent = package_div.parent
            for _ in range(5):  # Go up the DOM tree to find container
                if parent:
                    # Look for table within this container
                    table = parent.find('table')
                    if table:
                        # Verify it's a calendar table by looking for room type rows
                        if self._is_calendar_table(table):
                            return table
                    parent = parent.parent
                else:
                    break
            
            # Fallback: look for any calendar table after this package in the DOM
            current = package_div
            for _ in range(20):  # Look ahead in DOM
                current = current.find_next_sibling()
                if current is None:
                    break
                if current.name == 'table' and self._is_calendar_table(current):
                    return current
                # Also check for tables within siblings
                table = current.find('table') if hasattr(current, 'find') else None
                if table and self._is_calendar_table(table):
                    return table
            
            return None
            
        except Exception as e:
            print(f"Error finding calendar table: {e}")
            return None
    
    def _is_calendar_table(self, table) -> bool:
        """Check if a table is a calendar table with room types"""
        try:
            # Look for specific indicators that this is a calendar table
            table_text = table.get_text().lower()
            
            # Should contain room type indicators
            room_indicators = ['tatami mats', 'japanese', 'room type']
            calendar_indicators = ['○', '×', '-', 'vacancy', 'fully booked']
            
            has_room_indicator = any(indicator in table_text for indicator in room_indicators)
            has_calendar_indicator = any(indicator in table_text for indicator in calendar_indicators)
            
            return has_room_indicator and has_calendar_indicator
            
        except Exception as e:
            print(f"Error checking if calendar table: {e}")
            return False
    
    def _extract_room_types_from_calendar_table(self, table, package_name: str) -> List[Dict]:
        """Extract room types from a calendar table"""
        try:
            room_types = []
            
            # Find all rows in the table
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:  # Need at least room type and one date column
                    
                    # Look for room type in the second cell (first is usually image)
                    room_cell = None
                    for i, cell in enumerate(cells[:3]):  # Check first 3 cells
                        cell_text = cell.get_text(strip=True)
                        if 'tatami mats' in cell_text.lower():
                            room_cell = cell
                            break
                    
                    if room_cell:
                        room_type_text = room_cell.get_text(strip=True)
                        
                        # Clean up the room type name
                        room_type_name = re.sub(r'禁煙.*', '', room_type_text).strip()
                        
                        # Combine package name with room type
                        full_name = f"{package_name} - {room_type_name}"
                        
                        room_types.append({
                            'name': full_name,
                            'package_name': package_name,
                            'room_type': room_type_name,
                            'element': row,
                            'price': None  # Will be extracted during availability check
                        })
                        print(f"      Found room type: {room_type_name} in {package_name}")
            
            return room_types
            
        except Exception as e:
            print(f"Error extracting room types from calendar table: {e}")
            return []
    
    def _clean_package_name(self, text: str) -> str:
        """Clean and extract the package name from text"""
        try:
            # Look for patterns like "Traditional Gassho House (1 Night with 2 meals)★JUL～OCT★"
            # or "Traditional Gassho house (1 Night with 2 meals)☆NOV～☆"
            match = re.search(r'(Traditional Gassho[^★☆]*[★☆][^★☆]*[★☆])', text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            
            # Look for pattern with ☆ symbols specifically
            match = re.search(r'(Traditional Gassho[^☆]*☆[^☆]*☆)', text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            
            # Fallback: look for any text starting with "Traditional Gassho" up to a line break or specific chars
            match = re.search(r'(Traditional Gassho[^.\n\r\t]*)', text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                # Remove trailing punctuation except for special symbols
                result = re.sub(r'[.!?]+$', '', result)
                return result
            
            return text.strip()
            
        except Exception as e:
            print(f"Error cleaning package name: {e}")
            return text.strip()
    
    async def _fetch_dynamic_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page with dynamic JavaScript content using Playwright"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
            
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to the page
                await page.goto(url)
                
                # Wait for calendar content to load (look for calendar containers)
                try:
                    await page.wait_for_selector('#stock_calendar_1, #stock_calendar_2', timeout=10000)
                    # Give a bit more time for AJAX content to load
                    await page.wait_for_timeout(2000)
                except:
                    # If calendar containers don't appear, still try to get the content
                    await page.wait_for_timeout(3000)
                
                # Get the page content
                content = await page.content()
                await browser.close()
                
                return BeautifulSoup(content, 'html.parser')
                
        except Exception as e:
            print(f"Error fetching dynamic page with Playwright: {e}")
            return None
    
    def _are_similar_room_names(self, name1: str, name2: str) -> bool:
        """Check if two room names are similar (to avoid duplicates)"""
        # First check if they're exactly the same
        if name1.strip().lower() == name2.strip().lower():
            return True
        
        # Check for different seasonal packages (these should NOT be considered similar)
        seasonal_indicators = ['jul', 'oct', 'nov', 'mar', '★', '☆']
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # If both have seasonal indicators but different ones, they're different packages
        name1_has_seasonal = any(indicator in name1_lower for indicator in seasonal_indicators)
        name2_has_seasonal = any(indicator in name2_lower for indicator in seasonal_indicators)
        
        if name1_has_seasonal and name2_has_seasonal:
            # Check if they have different season indicators
            name1_seasons = [ind for ind in seasonal_indicators if ind in name1_lower]
            name2_seasons = [ind for ind in seasonal_indicators if ind in name2_lower]
            
            if name1_seasons != name2_seasons:
                return False  # Different seasonal packages
        
        # Standard similarity check for other cases
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        
        # If they share more than 80% of words, consider them similar (increased threshold)
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union)
        return similarity > 0.8
    
    def _check_room_type_availability(self, soup: BeautifulSoup, room_type: Dict, target_dt: datetime) -> Dict:
        """Check availability for a specific room type based on calendar table row"""
        try:
            room_element = room_type.get('element')  # This is the table row
            
            if room_element and room_element.name == 'tr':
                # Parse the calendar row for the target date
                availability_info = self._parse_calendar_row_for_date(room_element, target_dt)
                
                if availability_info:
                    return availability_info
            
            # Fallback to general calendar availability
            general_availability = self._parse_calendar_availability(soup, target_dt)
            if general_availability is not None:
                return {
                    'status': 'available' if general_availability else 'not_available',
                    'price': room_type.get('price')
                }
            
            # If no specific availability found, assume not available
            return {
                'status': 'not_available',
                'price': room_type.get('price')
            }
            
        except Exception as e:
            print(f"Error checking room type availability: {e}")
            return {
                'status': 'error',
                'price': room_type.get('price')
            }
    
    def _parse_calendar_row_for_date(self, row_element, target_dt: datetime) -> Optional[Dict]:
        """Parse a calendar table row for availability on target date"""
        try:
            cells = row_element.find_all(['td', 'th'])
            
            # Find the header row to get date positions
            table = row_element.find_parent('table')
            if not table:
                return None
            
            header_row = None
            for row in table.find_all('tr'):
                row_text = row.get_text().lower()
                if any(month in row_text for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                                      'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                                                      '/', '(']):
                    header_row = row
                    break
            
            if not header_row:
                return None
            
            header_cells = header_row.find_all(['td', 'th'])
            
            # Find which column corresponds to our target date
            target_column = None
            for i, header_cell in enumerate(header_cells):
                header_text = header_cell.get_text(strip=True)
                # Look for the target date in format like "4/15 (Mon)" or "8/15 (Fri)"
                if self._is_target_date_cell(header_text, target_dt):
                    target_column = i
                    break
            
            if target_column is None or target_column >= len(cells):
                return None
            
            # Get the availability cell
            availability_cell = cells[target_column]
            cell_text = availability_cell.get_text(strip=True)
            
            # Parse availability based on symbols
            if '○' in cell_text:  # Available
                # Try to extract price if available
                price_match = re.search(r'JPY([\d,]+)', cell_text)
                price = f"JPY{price_match.group(1)}" if price_match else None
                
                return {
                    'status': 'available',
                    'price': price
                }
            elif '×' in cell_text:  # Fully booked
                return {
                    'status': 'not_available',
                    'price': None
                }
            elif '-' in cell_text:  # No setup
                return {
                    'status': 'no_setup',
                    'price': None
                }
            
            return None
            
        except Exception as e:
            print(f"Error parsing calendar row: {e}")
            return None
    
    def _is_target_date_cell(self, header_text: str, target_dt: datetime) -> bool:
        """Check if a header cell text matches our target date"""
        try:
            # Look for patterns like "8/15 (Fri)" or "11/6 (Thu)"
            date_match = re.search(r'(\d{1,2})/(\d{1,2})', header_text)
            if date_match:
                month = int(date_match.group(1))
                day = int(date_match.group(2))
                
                return month == target_dt.month and day == target_dt.day
            
            # Alternative pattern: look for just the day
            if header_text.isdigit():
                day = int(header_text)
                return day == target_dt.day
            
            return False
            
        except Exception as e:
            print(f"Error checking target date cell: {e}")
            return False
    
    
    def _parse_calendar_availability(self, soup: BeautifulSoup, target_dt: datetime) -> Optional[bool]:
        """Parse calendar to check if target date is available"""
        try:
            # Look for calendar elements - common patterns in Japanese booking systems
            calendar_elements = (
                soup.find_all('td', class_=lambda x: x and any(cls in x for cls in ['calendar', 'cal', 'date'])) +
                soup.find_all('div', class_=lambda x: x and any(cls in x for cls in ['calendar', 'cal', 'date'])) +
                soup.find_all('span', class_=lambda x: x and any(cls in x for cls in ['calendar', 'cal', 'date']))
            )
            
            target_day = target_dt.day
            target_month = target_dt.month
            target_year = target_dt.year
            
            # Look for the specific date
            for element in calendar_elements:
                text = element.get_text(strip=True)
                
                # Check if this element represents our target date
                if text.isdigit() and int(text) == target_day:
                    # Check the classes or nearby elements for availability indicators
                    classes = element.get('class', [])
                    
                    # Common availability indicators
                    available_indicators = ['available', 'open', 'ok', 'circle', '○', '◯']
                    unavailable_indicators = ['unavailable', 'closed', 'full', 'x', '×', '✕']
                    
                    element_text = str(element).lower()
                    
                    # Check for availability indicators
                    if any(indicator in element_text for indicator in available_indicators):
                        return True
                    elif any(indicator in element_text for indicator in unavailable_indicators):
                        return False
                    
                    # Check classes for availability
                    class_str = ' '.join(classes).lower()
                    if any(indicator in class_str for indicator in available_indicators):
                        return True
                    elif any(indicator in class_str for indicator in unavailable_indicators):
                        return False
            
            # Look for JSON data or JavaScript variables that might contain calendar data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'calendar' in script.string.lower():
                    # Try to extract calendar data from JavaScript
                    calendar_data = self._extract_calendar_from_script(script.string, target_dt)
                    if calendar_data is not None:
                        return calendar_data
            
            return None
            
        except Exception as e:
            print(f"Error parsing calendar: {e}")
            return None
    
    def _extract_calendar_from_script(self, script_content: str, target_dt: datetime) -> Optional[bool]:
        """Extract calendar availability from JavaScript content"""
        try:
            # Look for common patterns in Japanese booking systems
            target_date_str = target_dt.strftime('%Y-%m-%d')
            target_date_alt = target_dt.strftime('%Y/%m/%d')
            target_day = str(target_dt.day)
            
            # Common patterns for availability in JS
            if target_date_str in script_content or target_date_alt in script_content:
                # Look for availability indicators near the date
                lines = script_content.split('\n')
                for line in lines:
                    if target_date_str in line or target_date_alt in line:
                        if any(word in line.lower() for word in ['available', 'open', 'ok', 'true']):
                            return True
                        elif any(word in line.lower() for word in ['unavailable', 'closed', 'false', 'full']):
                            return False
            
            return None
            
        except Exception as e:
            print(f"Error extracting from script: {e}")
            return None
    
    def _navigate_to_target_month(self, base_url: str, target_dt: datetime) -> Optional[bool]:
        """Navigate through calendar pages to find target month"""
        try:
            current_url = base_url
            max_attempts = 6  # Don't navigate more than 6 months
            
            for attempt in range(max_attempts):
                response = self.session.get(current_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check if we're in the right month
                availability = self._parse_calendar_availability(soup, target_dt)
                if availability is not None:
                    return availability
                
                # Look for next/previous month navigation
                next_link = self._find_navigation_link(soup, 'next')
                if next_link:
                    current_url = next_link if next_link.startswith('http') else urljoin(base_url, next_link)
                else:
                    break
            
            return None
            
        except Exception as e:
            print(f"Error navigating calendar: {e}")
            return None
    
    
    def _find_navigation_link(self, soup: BeautifulSoup, direction: str) -> Optional[str]:
        """Find next/previous month navigation links"""
        try:
            # Common navigation patterns
            nav_patterns = [
                f'a[href*="{direction}"]',
                f'a[class*="{direction}"]',
                'a[href*="month"]',
                'a[href*="calendar"]'
            ]
            
            direction_indicators = {
                'next': ['next', '次', '→', '>', 'forward'],
                'prev': ['prev', 'previous', '前', '←', '<', 'back']
            }
            
            indicators = direction_indicators.get(direction, [])
            
            # Look for navigation links
            for pattern in nav_patterns:
                links = soup.select(pattern)
                for link in links:
                    text = link.get_text(strip=True).lower()
                    href = link.get('href', '')
                    
                    if any(indicator in text for indicator in indicators):
                        return href
                    if any(indicator in href.lower() for indicator in indicators):
                        return href
            
            return None
            
        except Exception as e:
            print(f"Error finding navigation: {e}")
            return None
    
    def _write_accommodation_log(self):
        """Write accommodation log to file for debugging"""
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            log_filename = f"accommodation_log_{timestamp}.json"
            
            # Create summary statistics
            summary = {
                "total_accommodations": len(set(entry['id'] for entry in self.accommodation_log)),
                "no_booking_system": len([e for e in self.accommodation_log if e['final_status'] == 'no_booking_system']),
                "errors": len([e for e in self.accommodation_log if e['final_status'] == 'error']),
                "successful_checks": len([e for e in self.accommodation_log if e['final_status'] in ['available', 'not_available', 'multiple_room_types']]),
                "with_room_types": len([e for e in self.accommodation_log if e['room_types_found'] > 0])
            }
            
            log_data = {
                "timestamp": timestamp,
                "summary": summary,
                "accommodations": self.accommodation_log
            }
            
            with open(log_filename, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n=== ACCOMMODATION LOG SUMMARY ===")
            print(f"Total accommodations: {summary['total_accommodations']}")
            print(f"No booking system: {summary['no_booking_system']}")
            print(f"Errors: {summary['errors']}")
            print(f"Successful checks: {summary['successful_checks']}")
            print(f"With room types detected: {summary['with_room_types']}")
            print(f"Detailed log saved to: {log_filename}")
            
            # Print problematic accommodations
            problematic = [e for e in self.accommodation_log if e['final_status'] in ['no_booking_system', 'error']]
            if problematic:
                print(f"\n=== PROBLEMATIC ACCOMMODATIONS ===")
                for entry in problematic[:10]:  # Show first 10
                    print(f"- {entry['name']} (ID: {entry['id']}): {entry['final_status']}")
                    if entry['error']:
                        print(f"  Error: {entry['error'][:100]}...")
                    print(f"  URL: {entry['url']}")
                    if entry['reservation_url']:
                        print(f"  Reservation URL: {entry['reservation_url']}")
                    print()
            
        except Exception as e:
            print(f"Error writing accommodation log: {e}")
    
    def get_event_info(self) -> Dict:
        """Get basic event information"""
        return {
            "name": "Shirakawa-go Accommodation Availability",
            "venue": "Shirakawa-go, Japan",
            "url": self.root_page,
            "target_dates": self.target_dates,
            "type": "accommodation"
        }