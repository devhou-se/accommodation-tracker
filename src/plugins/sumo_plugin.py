import re
import requests
from typing import Dict, List
from datetime import datetime
from bs4 import BeautifulSoup
from .base import TicketPlugin, TicketAvailability, CheckResult


class SumoPlugin(TicketPlugin):
    """Plugin for checking Sumo wrestling ticket availability"""
    
    def __init__(self, config: Dict):
        super().__init__("sumo", config)
        self.base_url = config.get("url", "https://sumo.pia.jp/en/")
        self.tournament_month = config.get("tournament_month", "11")  # November
        self.year = config.get("year", "2025")
    
    async def check_availability(self) -> CheckResult:
        """Check Sumo tournament ticket availability"""
        try:
            # First check the main page for tournament status
            main_soup = self._fetch_page(self.base_url)
            main_availabilities = self._extract_availability_data(main_soup, self.base_url)
            
            # Also check the specific tournament page if it exists
            tournament_url = f"{self.base_url}sumo{self.tournament_month}.jsp"
            try:
                tournament_soup = self._fetch_page(tournament_url)
                tournament_availabilities = self._extract_availability_data(tournament_soup, tournament_url)
                # Combine results, preferring more detailed tournament page results
                if tournament_availabilities:
                    main_availabilities.extend(tournament_availabilities)
            except:
                # Tournament page might not exist yet or failed to load
                pass
            
            return CheckResult(
                plugin_name=self.name,
                item_name=f"{self.year} {self._get_month_name()} Grand Tournament",
                check_time=datetime.now(),
                availabilities=main_availabilities,
                success=True
            )
            
        except Exception as e:
            return CheckResult(
                plugin_name=self.name,
                item_name=f"{self.year} {self._get_month_name()} Grand Tournament",
                check_time=datetime.now(),
                availabilities=[],
                success=False,
                error_message=str(e)
            )
    
    def _fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch and parse a web page"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    
    def _extract_availability_data(self, soup: BeautifulSoup, url: str) -> List[TicketAvailability]:
        """Extract ticket availability data from the page"""
        availabilities = []
        
        try:
            page_text = soup.get_text()
            
            # Check for explicit sold out messages specifically for our tournament
            tournament_section = soup.find('p', string=lambda text: text and f"{self._get_month_name()} Grand Tournament" in text)
            if tournament_section and ("sold out" in tournament_section.get_text().lower() or "tickets are sold out" in tournament_section.get_text().lower()):
                availabilities.append(TicketAvailability(
                    date="All dates",
                    room_type="All seats",
                    status="sold_out",
                    price="Tournament sold out"
                ))
                return availabilities
            
            # Look for the main tournament table (on homepage)
            tournament_tables = soup.find_all('table', class_='table-pc-en')
            for table in tournament_tables:
                rows = table.find_all('tr')
                for row in rows:
                    # Find tournament name in th tag
                    tournament_header = row.find('th')
                    if tournament_header:
                        tournament_name = tournament_header.get_text(strip=True)
                        if self.year in tournament_name and self._get_month_name() in tournament_name:
                            # This is our target tournament row
                            cells = row.find_all('td')
                            if len(cells) >= 4:  # dates, venue, sale date, ticket info, buying tickets
                                # Last cell contains the "Buying Tickets" info
                                buying_tickets_cell = cells[-1]
                                
                                # Check for active buying link (not commented out)
                                buying_link = buying_tickets_cell.find('a')
                                dash_element = buying_tickets_cell.find('p')
                                
                                if buying_link and buying_link.get('href'):
                                    # Active link means tickets are available
                                    href = buying_link.get('href', '')
                                    if not href.startswith('http'):
                                        # Construct proper URL, handling relative paths
                                        if href.startswith('/'):
                                            # Absolute path
                                            base_domain = self.base_url.split('/')[0:3]  # ['https:', '', 'sumo.pia.jp']
                                            href = '/'.join(base_domain) + href
                                        else:
                                            # Relative path
                                            base = self.base_url.rstrip('/')
                                            href = f"{base}/{href}"
                                    
                                    availabilities.append(TicketAvailability(
                                        date="Tournament period",
                                        room_type="All seat types",
                                        status="available",
                                        booking_url=href,
                                        price="Tickets available for purchase",
                                        venue=self._get_venue()
                                    ))
                                    return availabilities  # Found our target, return immediately
                                # Skip "not_on_sale" entries - only show when tickets are available
                                # elif dash_element and "―" in dash_element.get_text():
                                #     # Dash means not yet on sale
                                #     availabilities.append(TicketAvailability(
                                #         date="Tournament period",
                                #         room_type="All seat types", 
                                #         status="not_on_sale",
                                #         price="Tickets not yet on sale",
                                #         venue=self._get_venue(),
                                #         booking_url=self.base_url  # Link to main page for information
                                #     ))
                                #     return availabilities  # Found our target, return immediately
                            break
            
            # If we're on a specific tournament page, check for detailed availability
            if f"sumo{self.tournament_month}.jsp" in url:
                # Check for sale date information
                sale_date_pattern = r"Goes on Sale[：:]\s*([^*\n]+)"
                sale_date_match = re.search(sale_date_pattern, page_text)
                
                # Skip adding "not_on_sale" entries - only show when tickets are actually available
                # if sale_date_match:
                #     sale_date = sale_date_match.group(1).strip()
                #     availabilities.append(TicketAvailability(
                #         date="Sale information",
                #         room_type="All seats",
                #         status="not_on_sale",
                #         price=f"Sale starts: {sale_date}"
                #     ))
                
                # Check for specific booking buttons/links
                booking_links = soup.find_all('a', href=lambda x: x and 'sell.pia.jp' in x)
                for link in booking_links:
                    href = link.get('href', '')
                    
                    # Skip placeholder URLs (contain ●●● or similar placeholder text)
                    if "●●●" in href or "eventCd=" not in href or href.count("=") < 2:
                        continue
                        
                    # Try to get seat type from nearby text or image
                    link_text = link.get_text(strip=True)
                    img = link.find('img')
                    if img and img.get('alt'):
                        link_text = img.get('alt')
                    
                    # Determine seat type
                    if "box" in link_text.lower() and "special" not in link_text.lower():
                        room_type = "Box Seats (4 guests)"
                    elif "special" in link_text.lower():
                        room_type = "Special Box (2 guests)"
                    elif "chair" in link_text.lower() or "arena" in link_text.lower():
                        room_type = "Chair Seats"
                    else:
                        room_type = "Tickets"
                    
                    availabilities.append(TicketAvailability(
                        date="Tournament dates",
                        room_type=room_type,
                        status="available",
                        booking_url=href,
                        venue=self._get_venue()
                    ))
            
            # If no availability data found, don't add fallback entries
            # Just return empty list - only show actual ticket availability
            # if not availabilities:
            #     availabilities.append(TicketAvailability(
            #         date="Status unknown",
            #         room_type="All seats",
            #         status="unknown",
            #         price="Could not determine ticket status",
            #         venue=self._get_venue(),
            #         booking_url=self.base_url  # Link to main page for information
            #     ))
        
        except Exception as e:
            # Log error but don't fail completely
            print(f"Error extracting availability data: {e}")
            availabilities.append(TicketAvailability(
                date="Error",
                room_type="All seats",
                status="error",
                price=f"Error checking: {str(e)}"
            ))
        
        return availabilities
    
    def get_event_info(self) -> Dict:
        """Get basic event information"""
        return {
            "name": f"{self.year} {self._get_month_name()} Grand Tournament",
            "venue": self._get_venue(),
            "month": self.tournament_month,
            "year": self.year,
            "url": self.base_url
        }
    
    def get_item_info(self) -> Dict:
        """Get basic item information - required by BookingPlugin base class"""
        return self.get_event_info()  # For sumo, item info is the same as event info
    
    def _get_month_name(self) -> str:
        """Get month name from month number"""
        months = {
            "01": "January", "03": "March", "05": "May", 
            "07": "July", "09": "September", "11": "November"
        }
        return months.get(self.tournament_month, f"Month {self.tournament_month}")
    
    def _get_venue(self) -> str:
        """Get venue based on tournament month"""
        venues = {
            "01": "Tokyo (Ryogoku Kokugikan)",
            "03": "Osaka",
            "05": "Tokyo (Ryogoku Kokugikan)",
            "07": "Nagoya",
            "09": "Tokyo (Ryogoku Kokugikan)",
            "11": "Fukuoka"
        }
        return venues.get(self.tournament_month, "Unknown venue")