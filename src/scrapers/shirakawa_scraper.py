import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, AccommodationResult


class ShirakawaScraper(BaseScraper):
    """Scraper for Shirakawa-go accommodation booking sites."""
    
    SEARCH_URL = "https://shirakawa-go.gr.jp/en/stay/?tag%5B%5D=1&category%5B%5D=3#refine"
    
    def __init__(self, timeout_seconds: int = 30):
        super().__init__(timeout_seconds)
        self.playwright = None
        self.browser = None
        self.context = None
    
    async def _initialize_browser(self):
        """Initialize Playwright browser."""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.logger.info("Browser initialized")
    
    async def check_availability(self, target_dates: List[str]) -> List[AccommodationResult]:
        """Check availability for all Gassho houses in Ogimachi area."""
        await self._initialize_browser()
        
        results = []
        
        try:
            # Get list of accommodations
            accommodations = await self._get_accommodation_list()
            self.logger.info("Found accommodations", count=len(accommodations))
            
            # Check each accommodation
            for acc_info in accommodations:
                try:
                    availability = await self._check_single_accommodation(acc_info, target_dates)
                    if availability:
                        results.append(availability)
                except Exception as e:
                    self.log_scraping_error(acc_info.get('name', 'Unknown'), str(e))
                    continue
                    
                # Add delay between requests to be respectful
                await asyncio.sleep(2)
                
        except Exception as e:
            self.logger.error("Error during availability checking", error=str(e))
            raise
        
        return results
    
    async def _get_accommodation_list(self) -> List[Dict[str, str]]:
        """Extract accommodation list from the search results page."""
        page = await self.context.new_page()
        
        try:
            await page.goto(self.SEARCH_URL, timeout=self.timeout_seconds * 1000)
            await page.wait_for_load_state('networkidle')
            
            # Extract accommodation links and names
            accommodations = []
            
            # Find direct links with the ./[number]/ pattern
            links = await page.locator('a[href^="./"]').all()
            
            for link in links:
                try:
                    href = await link.get_attribute('href')
                    if href and re.match(r'^\./\d+/$', href):
                        # Try to get the accommodation name from h5 element within the link
                        name_element = link.locator('h5')
                        if await name_element.count() > 0:
                            name = await name_element.text_content()
                            name = name.strip() if name else 'Unknown'
                        else:
                            # Fallback: get first line of text content
                            text_content = await link.text_content()
                            if text_content:
                                lines = text_content.strip().split('\n')
                                name = lines[0].strip() if lines else 'Unknown'
                            else:
                                name = f"Accommodation {href.strip('./')}"
                        
                        # Convert relative URL to absolute
                        full_url = f"https://shirakawa-go.gr.jp/en/stay/{href.strip('./')}"
                        
                        accommodations.append({
                            'name': name,
                            'url': full_url
                        })
                        
                        self.logger.debug("Found accommodation", name=name, url=full_url)
                        
                except Exception as e:
                    self.logger.debug("Error processing accommodation link", error=str(e))
                    continue
            
            # If no accommodations found, log the page content for debugging
            if not accommodations:
                self.logger.warning("No accommodations found, checking page content")
                # Let's see what links are actually on the page
                all_links = await page.locator('a').all()
                for i, link in enumerate(all_links[:10]):  # Just first 10 for debugging
                    href = await link.get_attribute('href')
                    text = await link.text_content()
                    self.logger.debug(f"Link {i}", href=href, text=text[:100] if text else None)
            
            return accommodations
            
        finally:
            await page.close()
    
    async def _check_single_accommodation(self, acc_info: Dict[str, str], target_dates: List[str]) -> Optional[AccommodationResult]:
        """Check availability for a single accommodation."""
        page = await self.context.new_page()
        
        try:
            self.logger.debug("Checking accommodation", name=acc_info['name'], url=acc_info['url'])
            
            # Go to accommodation page
            await page.goto(acc_info['url'], timeout=self.timeout_seconds * 1000)
            await page.wait_for_load_state('networkidle')
            
            # Find reservation link - try different possible text patterns
            reservation_selectors = [
                'a:has-text("Click here for reservations")',
                'a[href*="489pro.com"]',
                'a[href*="menu.asp"]'
            ]
            
            reservation_link = None
            for selector in reservation_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        reservation_link = await element.get_attribute('href')
                        break
                except:
                    continue
            
            if not reservation_link:
                self.logger.warning("No reservation link found", accommodation=acc_info['name'])
                return None
            
            # Go to reservation page
            await page.goto(reservation_link, timeout=self.timeout_seconds * 1000)
            await page.wait_for_load_state('networkidle')
            
            # Find calendar links for each room type
            calendar_links = await page.locator('a:has-text("calendar")').all()
            
            available_dates = set()
            
            for calendar_link in calendar_links:
                try:
                    calendar_url = await calendar_link.get_attribute('href')
                    if calendar_url:
                        room_dates = await self._check_calendar_page(page, calendar_url, target_dates)
                        available_dates.update(room_dates)
                except Exception as e:
                    self.logger.warning("Error checking calendar", 
                                      accommodation=acc_info['name'], 
                                      error=str(e))
                    continue
            
            # Filter to only target dates
            matching_dates = self.filter_available_dates(target_dates, list(available_dates))
            
            if matching_dates:
                self.log_availability_found(acc_info['name'], matching_dates)
                return AccommodationResult(
                    accommodation_name=acc_info['name'],
                    available_dates=matching_dates,
                    link=reservation_link,
                    location="Ogimachi, Shirakawa-go"
                )
            else:
                self.log_no_availability(acc_info['name'])
                return None
                
        finally:
            await page.close()
    
    async def _check_calendar_page(self, page: Page, calendar_url: str, target_dates: List[str]) -> List[str]:
        """Check a specific calendar page for availability."""
        # Navigate to calendar
        await page.goto(calendar_url, timeout=self.timeout_seconds * 1000)
        await page.wait_for_load_state('networkidle')
        
        available_dates = []
        
        # Look for calendar cells with availability markers (○ symbol)
        # These are typically in links with text containing ○ and JPY prices
        available_cells = await page.locator('a:has-text("○"):has-text("JPY")').all()
        
        for cell in available_cells:
            cell_text = await cell.text_content()
            if cell_text and '○' in cell_text:
                # Extract date from cell text (format like "8/27 ○ JPY15,400")
                date_match = re.search(r'(\d+)/(\d+)', cell_text)
                if date_match:
                    month, day = date_match.groups()
                    
                    # Get current year from calendar context or page
                    # Look for year information in the calendar header
                    year_text = await page.locator('text=/2025|2024/').first.text_content()
                    year = '2025'  # Default, but try to extract from page
                    if year_text:
                        year_match = re.search(r'(202[4-9])', year_text)
                        if year_match:
                            year = year_match.group(1)
                    
                    # Format as YYYY-MM-DD
                    formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    available_dates.append(formatted_date)
        
        return available_dates
    
    async def cleanup(self):
        """Clean up browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.logger.info("Browser resources cleaned up")