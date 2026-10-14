import os
import re
import sys
import certifi
import airportsdata
import pycountry
import requests
from dotenv import load_dotenv

from exception import CustomException
from logger import logger

# =====================================================================
# STEP 1: Environment Setup & API Configuration
# =====================================================================
try:
    logger.info("Step 1: Loading environment variables from .env file...")
    load_dotenv()

    logger.info("Step 1: Configuring SSL certificate paths with certifi...")
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

    API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
    if not API_KEY:
        logger.warning("Step 1: AVIATIONSTACK_API_KEY is not set in environment or .env file.")
    else:
        logger.info("Step 1: AVIATIONSTACK_API_KEY loaded successfully.")

    # Default origin when user says only destination, e.g. "Japan trip"
    DEFAULT_ORIGIN_IATA = os.getenv("DEFAULT_ORIGIN_IATA", "DAC")
    BASE_URL = "https://api.aviationstack.com/v1/flights"

    logger.info("Step 1: Loading IATA airport database using airportsdata...")
    AIRPORTS = airportsdata.load("IATA")
    logger.info(f"Step 1: Loaded {len(AIRPORTS)} airports into memory successfully.")

except Exception as e:
    logger.error(f"Step 1: Error during environment/database initialization: {e}")
    raise CustomException(e, sys)


# =====================================================================
# Reference Mappings & Aliases
# =====================================================================
COUNTRY_ALIASES = {
    "usa": "US",
    "u.s.a": "US",
    "u.s.": "US",
    "america": "US",
    "united states": "US",
    "uk": "GB",
    "u.k.": "GB",
    "britain": "GB",
    "england": "GB",
    "uae": "AE",
    "dubai": "AE",
    "south korea": "KR",
    "korea": "KR",
    "russia": "RU",
    "vietnam": "VN",
    "bangladesh": "BD",
    "india": "IN",
    "japan": "JP",
    "china": "CN",
    "singapore": "SG",
    "malaysia": "MY",
    "thailand": "TH",
    "indonesia": "ID",
    "nepal": "NP",
    "qatar": "QA",
    "saudi arabia": "SA",
    "turkey": "TR",
    "canada": "CA",
    "australia": "AU",
    "germany": "DE",
    "france": "FR",
    "italy": "IT",
    "spain": "ES",
}

COUNTRY_MAIN_AIRPORT = {
    "BD": "DAC",
    "IN": "DEL",
    "JP": "NRT",
    "US": "JFK",
    "GB": "LHR",
    "AE": "DXB",
    "SG": "SIN",
    "MY": "KUL",
    "TH": "BKK",
    "ID": "CGK",
    "CN": "PEK",
    "KR": "ICN",
    "NP": "KTM",
    "QA": "DOH",
    "SA": "JED",
    "TR": "IST",
    "CA": "YYZ",
    "AU": "SYD",
    "DE": "FRA",
    "FR": "CDG",
    "IT": "FCO",
    "ES": "MAD",
}

CITY_MAIN_AIRPORT = {
    "dhaka": "DAC",
    "delhi": "DEL",
    "new delhi": "DEL",
    "mumbai": "BOM",
    "kolkata": "CCU",
    "chennai": "MAA",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "tokyo": "NRT",
    "osaka": "KIX",
    "kyoto": "KIX",
    "new york": "JFK",
    "london": "LHR",
    "dubai": "DXB",
    "singapore": "SIN",
    "kuala lumpur": "KUL",
    "bangkok": "BKK",
    "doha": "DOH",
    "istanbul": "IST",
    "toronto": "YYZ",
    "sydney": "SYD",
    "paris": "CDG",
    "rome": "FCO",
    "madrid": "MAD",
    "frankfurt": "FRA",
}


# =====================================================================
# STEP 2: Text Cleaning & Normalization
# =====================================================================
def clean_text(text: str) -> str:
    """
    Cleans query text by lowercasing, stripping punctuation, and removing common travel stop words.
    """
    try:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        stop_words = [
            "flight", "flights", "ticket", "tickets", "trip", "travel",
            "plan", "complete", "days", "day", "including", "hotel",
            "hotels", "sightseeing", "under", "budget", "info", "information",
        ]
        words = [w for w in text.split() if w not in stop_words]
        cleaned = " ".join(words).strip()
        return cleaned
    except Exception as e:
        logger.error(f"Step 2: Error cleaning text '{text}': {e}")
        raise CustomException(e, sys)


# =====================================================================
# STEP 3: Country Name to ISO Alpha-2 Code Resolution
# =====================================================================
def country_name_to_code(text: str):
    """
    Converts a country name or alias to an ISO 3166-1 alpha-2 code.
    """
    try:
        cleaned_text = clean_text(text)
        logger.info(f"Step 3: Resolving country code for cleaned text: '{cleaned_text}'")

        if cleaned_text in COUNTRY_ALIASES:
            code = COUNTRY_ALIASES[cleaned_text]
            logger.info(f"Step 3: Found country code '{code}' in COUNTRY_ALIASES for '{cleaned_text}'")
            return code

        try:
            country = pycountry.countries.lookup(cleaned_text)
            logger.info(f"Step 3: Found country code '{country.alpha_2}' via pycountry for '{cleaned_text}'")
            return country.alpha_2
        except LookupError:
            pass

        # Detect country name inside longer text
        for country in pycountry.countries:
            country_name = country.name.lower()
            if country_name in cleaned_text:
                logger.info(f"Step 3: Matched country name '{country.name}' -> code '{country.alpha_2}'")
                return country.alpha_2

        for alias, code in COUNTRY_ALIASES.items():
            if alias in cleaned_text:
                logger.info(f"Step 3: Matched country alias '{alias}' -> code '{code}'")
                return code

        logger.info(f"Step 3: No country code could be resolved for text: '{text}'")
        return None

    except Exception as e:
        logger.error(f"Step 3: Error in country_name_to_code for '{text}': {e}")
        raise CustomException(e, sys)


# =====================================================================
# STEP 4: Airport & Country Matching
# =====================================================================
def airport_country_matches(airport: dict, country_code: str) -> bool:
    """
    Checks if an airport dictionary belongs to the given country code.
    """
    try:
        airport_country = str(airport.get("country", "")).upper().strip()

        if airport_country == country_code:
            return True

        try:
            country = pycountry.countries.get(alpha_2=country_code)
            if country and airport_country.lower() == country.name.lower():
                return True
        except Exception:
            pass

        return False

    except Exception as e:
        logger.error(f"Step 4: Error checking country match for airport {airport} and country '{country_code}': {e}")
        raise CustomException(e, sys)


# =====================================================================
# STEP 5: Selecting the Best Airport for a Country
# =====================================================================
def get_best_airport_for_country(country_code: str):
    """
    Selects the primary international airport for a given country code.
    """
    try:
        logger.info(f"Step 5: Finding best airport for country code: '{country_code}'")
        preferred = COUNTRY_MAIN_AIRPORT.get(country_code)

        if preferred and preferred in AIRPORTS:
            logger.info(f"Step 5: Found preferred primary airport '{preferred}' for '{country_code}'")
            return preferred

        candidates = []
        for iata, airport in AIRPORTS.items():
            if not iata:
                continue

            if airport_country_matches(airport, country_code):
                name = str(airport.get("name", "")).lower()
                city = str(airport.get("city", "")).lower()

                score = 0
                if "international" in name:
                    score += 50
                if "intl" in name:
                    score += 40
                if "capital" in name:
                    score += 20
                if city:
                    score += 5

                candidates.append((score, iata))

        if not candidates:
            logger.warning(f"Step 5: No matching airport candidates found for country '{country_code}'")
            return None

        candidates.sort(reverse=True)
        best_airport = candidates[0][1]
        logger.info(f"Step 5: Selected best scored airport '{best_airport}' for country '{country_code}'")
        return best_airport

    except Exception as e:
        logger.error(f"Step 5: Error getting best airport for country '{country_code}': {e}")
        raise CustomException(e, sys)


# =====================================================================
# STEP 6: Location String to IATA Code Resolution
# =====================================================================
def resolve_location_to_iata(location: str):
    """
    Converts country/city/airport/IATA text into a 3-letter IATA code.
    """
    try:
        if not location:
            return None

        raw_location = location.strip()
        logger.info(f"Step 6: Resolving location to IATA: '{raw_location}'")

        # Direct 3-letter IATA code
        if re.fullmatch(r"[A-Za-z]{3}", raw_location):
            code = raw_location.upper()
            if code in AIRPORTS:
                logger.info(f"Step 6: Location '{raw_location}' matched direct valid IATA code: '{code}'")
                return code

        location_clean = clean_text(raw_location)
        if not location_clean:
            logger.warning(f"Step 6: Location '{raw_location}' was empty after cleaning")
            return None

        # Preferred city airport
        if location_clean in CITY_MAIN_AIRPORT:
            code = CITY_MAIN_AIRPORT[location_clean]
            logger.info(f"Step 6: Resolved city '{location_clean}' to preferred airport '{code}'")
            return code

        # Preferred country airport
        country_code = country_name_to_code(location_clean)
        if country_code:
            airport = get_best_airport_for_country(country_code)
            if airport:
                logger.info(f"Step 6: Resolved country '{location_clean}' ({country_code}) to airport '{airport}'")
                return airport

        # Database city matching
        city_matches = []
        for iata, airport in AIRPORTS.items():
            city = str(airport.get("city", "")).lower().strip()
            name = str(airport.get("name", "")).lower().strip()

            score = 0
            if city == location_clean:
                score += 100
            elif location_clean in city:
                score += 70

            if location_clean in name:
                score += 50

            if "international" in name:
                score += 10

            if score > 0:
                city_matches.append((score, iata))

        if city_matches:
            city_matches.sort(reverse=True)
            best_match = city_matches[0][1]
            logger.info(f"Step 6: Resolved '{location_clean}' via airport DB search to '{best_match}'")
            return best_match

        logger.warning(f"Step 6: Could not resolve location '{raw_location}' to any known IATA code")
        return None

    except Exception as e:
        logger.error(f"Step 6: Error resolving location '{location}' to IATA: {e}")
        raise CustomException(e, sys)


# =====================================================================
# STEP 7: Detect Location Mentions in Natural Query
# =====================================================================
def find_location_mentions(query: str):
    """
    Finds country or city names inside a natural language query.
    """
    try:
        q = query.lower()
        mentions = []
        logger.info(f"Step 7: Scanning query for location mentions: '{query}'")

        # Country aliases
        for alias in COUNTRY_ALIASES:
            if re.search(rf"\b{re.escape(alias)}\b", q):
                mentions.append(alias)

        # Country names from pycountry
        for country in pycountry.countries:
            name = country.name.lower()
            if len(name) >= 4 and re.search(rf"\b{re.escape(name)}\b", q):
                mentions.append(name)

        # City names from city map
        for city in CITY_MAIN_AIRPORT:
            if re.search(rf"\b{re.escape(city)}\b", q):
                mentions.append(city)

        # Remove duplicates while keeping order
        unique_mentions = []
        for item in mentions:
            if item not in unique_mentions:
                unique_mentions.append(item)

        logger.info(f"Step 7: Identified unique location mentions: {unique_mentions}")
        return unique_mentions

    except Exception as e:
        logger.error(f"Step 7: Error detecting location mentions in query '{query}': {e}")
        raise CustomException(e, sys)


# =====================================================================
# STEP 8: Parse Departure & Arrival Route
# =====================================================================
def parse_route(query: str):
    """
    Extracts origin and destination IATA codes from query string.
    """
    try:
        q = query.strip()
        q_lower = q.lower()
        logger.info(f"Step 8: Parsing flight route from query: '{query}'")

        # Global query check
        global_keywords = [
            "all country", "all countries", "global flight", "global flights",
            "all flight", "all flights", "worldwide flight", "worldwide flights",
        ]
        if any(keyword in q_lower for keyword in global_keywords):
            logger.info("Step 8: Global flight keywords detected - returning (None, None)")
            return None, None

        # Direct IATA code route: DAC to NRT
        codes = re.findall(r"\b[A-Z]{3}\b", q)
        if len(codes) >= 2:
            dep, arr = codes[0].upper(), codes[1].upper()
            logger.info(f"Step 8: Found explicit IATA codes: dep={dep}, arr={arr}")
            return dep, arr

        # Pattern: from X to Y
        match = re.search(
            r"\bfrom\s+(.+?)\s+\bto\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
            q_lower,
        )
        if match:
            origin_text = match.group(1)
            dest_text = match.group(2)
            logger.info(f"Step 8: Matched pattern 'from {origin_text} to {dest_text}'")
            dep_iata = resolve_location_to_iata(origin_text)
            arr_iata = resolve_location_to_iata(dest_text)
            logger.info(f"Step 8: Route parsed: dep={dep_iata}, arr={arr_iata}")
            return dep_iata, arr_iata

        # Pattern: to Y from X
        match = re.search(
            r"\bto\s+(.+?)\s+\bfrom\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
            q_lower,
        )
        if match:
            dest_text = match.group(1)
            origin_text = match.group(2)
            logger.info(f"Step 8: Matched pattern 'to {dest_text} from {origin_text}'")
            dep_iata = resolve_location_to_iata(origin_text)
            arr_iata = resolve_location_to_iata(dest_text)
            logger.info(f"Step 8: Route parsed: dep={dep_iata}, arr={arr_iata}")
            return dep_iata, arr_iata

        # Pattern: flights from X
        match = re.search(r"\bfrom\s+(.+?)(?:[.!?]|$)", q_lower)
        if match:
            origin_text = match.group(1)
            logger.info(f"Step 8: Matched pattern 'from {origin_text}'")
            dep_iata = resolve_location_to_iata(origin_text)
            logger.info(f"Step 8: Departure only route parsed: dep={dep_iata}")
            return dep_iata, None

        # Pattern: flights to X
        match = re.search(r"\bto\s+(.+?)(?:[.!?]|$)", q_lower)
        if match:
            dest_text = match.group(1)
            logger.info(f"Step 8: Matched pattern 'to {dest_text}'")
            arr_iata = resolve_location_to_iata(dest_text)
            logger.info(f"Step 8: Arrival only route parsed: arr={arr_iata}")
            return None, arr_iata

        # Fallback: location mentions
        logger.info("Step 8: Trying location mentions fallback...")
        mentions = find_location_mentions(q)

        if len(mentions) >= 2:
            dep_iata = resolve_location_to_iata(mentions[0])
            arr_iata = resolve_location_to_iata(mentions[1])
            logger.info(f"Step 8: Resolved route from mentions: dep={dep_iata}, arr={arr_iata}")
            return dep_iata, arr_iata

        if len(mentions) == 1:
            arr_iata = resolve_location_to_iata(mentions[0])
            logger.info(
                f"Step 8: Single mention '{mentions[0]}' detected. "
                f"Using default origin '{DEFAULT_ORIGIN_IATA}' -> arr='{arr_iata}'"
            )
            return DEFAULT_ORIGIN_IATA, arr_iata

        logger.info("Step 8: No route parsed, defaulting to global live flights (None, None)")
        return None, None

    except Exception as e:
        logger.error(f"Step 8: Error in parse_route for query '{query}': {e}")
        raise CustomException(e, sys)


# =====================================================================
# STEP 9: Format Individual Flight Record
# =====================================================================
def format_flight(flight: dict) -> str:
    """
    Formats a raw flight dictionary from AviationStack into a structured summary string.
    """
    try:
        airline = flight.get("airline", {}).get("name") or "Unknown airline"
        flight_number = flight.get("flight", {}).get("iata") or "Unknown flight number"
        status = flight.get("flight_status") or "Unknown"

        dep = flight.get("departure", {}) or {}
        arr = flight.get("arrival", {}) or {}

        dep_airport = dep.get("airport") or "Unknown departure airport"
        dep_iata = dep.get("iata") or "Unknown"
        dep_terminal = dep.get("terminal") or "N/A"
        dep_gate = dep.get("gate") or "N/A"
        dep_scheduled = dep.get("scheduled") or "Unknown"
        dep_delay = dep.get("delay")
        dep_delay_text = f"{dep_delay} minutes" if dep_delay is not None else "N/A"

        arr_airport = arr.get("airport") or "Unknown arrival airport"
        arr_iata = arr.get("iata") or "Unknown"
        arr_terminal = arr.get("terminal") or "N/A"
        arr_gate = arr.get("gate") or "N/A"
        arr_scheduled = arr.get("scheduled") or "Unknown"
        arr_delay = arr.get("delay")
        arr_delay_text = f"{arr_delay} minutes" if arr_delay is not None else "N/A"

        return f"""
Airline: {airline}
Flight: {flight_number}
Status: {status}

Departure:
- Airport: {dep_airport}
- IATA: {dep_iata}
- Terminal: {dep_terminal}
- Gate: {dep_gate}
- Scheduled: {dep_scheduled}
- Delay: {dep_delay_text}

Arrival:
- Airport: {arr_airport}
- IATA: {arr_iata}
- Terminal: {arr_terminal}
- Gate: {arr_gate}
- Scheduled: {arr_scheduled}
- Delay: {arr_delay_text}
""".strip()

    except Exception as e:
        logger.error(f"Step 9: Error formatting flight dictionary: {e}")
        raise CustomException(e, sys)


# =====================================================================
# STEP 10: Main Flight Search Execution
# =====================================================================
def search_flights(query: str, limit: int = 10) -> str:
    """
    Searches for live flights via the AviationStack API based on a natural language query.
    """
    try:
        logger.info(f"Step 10: Starting search_flights for query: '{query}' with limit={limit}")

        if not API_KEY:
            msg = (
                "Flight API error: AVIATIONSTACK_API_KEY is missing.\n"
                "Please add this in your .env file:\n"
                "AVIATIONSTACK_API_KEY=your_api_key_here"
            )
            logger.error("Step 10: AVIATIONSTACK_API_KEY is missing")
            return msg

        dep_iata, arr_iata = parse_route(query)

        params = {
            "access_key": API_KEY,
            "limit": min(limit, 100),
        }
        if dep_iata:
            params["dep_iata"] = dep_iata
        if arr_iata:
            params["arr_iata"] = arr_iata

        masked_params = {k: (v if k != "access_key" else "***") for k, v in params.items()}
        logger.info(f"Step 10: Requesting AviationStack API ({BASE_URL}) with params: {masked_params}")

        try:
            response = requests.get(BASE_URL, params=params, timeout=30)
            logger.info(f"Step 10: Received HTTP status code {response.status_code}")
            data = response.json()
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Step 10: Network error while requesting AviationStack API: {req_err}")
            return f"Flight API request failed: {req_err}"
        except ValueError as json_err:
            logger.error(f"Step 10: JSON parsing error from AviationStack API response: {json_err}")
            return "Flight API returned invalid JSON."

        if "error" in data:
            error = data["error"]
            err_code = error.get("code", "Unknown")
            err_msg = error.get("message", "Unknown error")
            logger.error(f"Step 10: AviationStack returned an API error: Code={err_code}, Message={err_msg}")
            return (
                "Flight API error:\n"
                f"Code: {err_code}\n"
                f"Message: {err_msg}"
            )

        flight_data = data.get("data", [])
        logger.info(f"Step 10: Retrieved {len(flight_data)} flight entries from API")

        if not flight_data:
            route_text = ""
            if dep_iata and arr_iata:
                route_text = f" for route {dep_iata} to {arr_iata}"
            elif dep_iata:
                route_text = f" from {dep_iata}"
            elif arr_iata:
                route_text = f" to {arr_iata}"

            logger.warning(f"Step 10: No live flight data found{route_text}")
            return (
                f"No live flight data found{route_text}.\n\n"
                "Note: AviationStack provides live/status flight data, not ticket prices. "
                "For actual fare prices, use a flight-pricing API such as Amadeus."
            )

        route_info = "Global live flights"
        if dep_iata and arr_iata:
            route_info = f"Live flights from {dep_iata} to {arr_iata}"
        elif dep_iata:
            route_info = f"Live flights from {dep_iata}"
        elif arr_iata:
            route_info = f"Live flights to {arr_iata}"

        num_flights_to_format = min(len(flight_data), limit)
        logger.info(f"Step 10: Formatting top {num_flights_to_format} flight results")
        formatted_flights = [format_flight(flight) for flight in flight_data[:limit]]

        result = f"{route_info}\n\n" + "\n\n---\n\n".join(formatted_flights)
        logger.info("Step 10: Flight search completed successfully.")
        return result

    except Exception as e:
        logger.error(f"Step 10: Unhandled exception in search_flights: {e}")
        raise CustomException(e, sys)


# =====================================================================
# Main Block for Standalone Testing
# =====================================================================
if __name__ == "__main__":
    try:
        logger.info("Starting flight_tool standalone test execution...")

        res1 = search_flights("Plan a 7 days Japan trip from Bangladesh")
        logger.info(f"Test 1 Search Result:\n{res1}")
        print(res1)

        print("\n" + "=" * 80 + "\n")

        res2 = search_flights("all country flight info")
        logger.info(f"Test 2 Search Result:\n{res2}")
        print(res2)

        logger.info("Completed flight_tool standalone test execution.")

    except Exception as e:
        logger.error(f"Error occurred during standalone test execution: {e}")
        raise CustomException(e, sys)