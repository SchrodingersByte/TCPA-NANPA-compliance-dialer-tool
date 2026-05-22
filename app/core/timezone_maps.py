"""
Static NANPA area-code → US state + IANA timezone routing table.

Resolution logic used by the compliance engine:
  1. Strip the leading '+1' from an E.164 number to isolate the 10-digit string.
  2. Take the first 3 digits as the area code.
  3. Look up that code in AREA_CODE_MAP to obtain (state_code, timezone).
  4. If the code is unknown, fall back to FEDERAL_FALLBACK.

All IANA timezone identifiers are compatible with Python's stdlib `zoneinfo`
(Python 3.9+) and pytz.

Notes on edge cases encoded here:
  - Florida 850 (Panhandle): state=FL but tz=America/Chicago (CT).
    The compliance engine applies FL's 20:00 cutoff in CT local time.
  - Indiana 219 (NW corner, Gary metro): CT, not ET like the rest of the state.
  - Kentucky is split; 270/364 are CT (western KY), rest ET.
  - Tennessee is split; 423/865 are ET (east), remainder CT.
  - Texas 915 (El Paso) is Mountain; all other TX codes are CT.
  - Arizona uses America/Phoenix (no DST) for all codes.
  - South Dakota 605 covers both CT (east) and MT (west); CT used as the
    dominant population timezone.
  - North Dakota 701 covers both CT (east) and MT (west); CT used as dominant.
"""

from typing import NamedTuple


class AreaCodeInfo(NamedTuple):
    state_code: str    # 2-letter USPS abbreviation
    state_name: str    # Full state/territory name
    timezone: str      # IANA timezone identifier


FEDERAL_FALLBACK = AreaCodeInfo("US", "Unknown / Federal Default", "America/New_York")

AREA_CODE_MAP: dict[str, AreaCodeInfo] = {

    # ─── EASTERN TIME  (America/New_York) ────────────────────────────────────

    # Connecticut
    "203": AreaCodeInfo("CT", "Connecticut", "America/New_York"),
    "475": AreaCodeInfo("CT", "Connecticut", "America/New_York"),
    "860": AreaCodeInfo("CT", "Connecticut", "America/New_York"),
    "959": AreaCodeInfo("CT", "Connecticut", "America/New_York"),

    # Delaware
    "302": AreaCodeInfo("DE", "Delaware", "America/New_York"),

    # District of Columbia
    "202": AreaCodeInfo("DC", "District of Columbia", "America/New_York"),

    # Florida (main peninsula — ET)
    "239": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "305": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "321": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "352": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "386": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "407": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "561": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "689": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "727": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "754": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "772": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "786": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "813": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "863": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "904": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "941": AreaCodeInfo("FL", "Florida", "America/New_York"),
    "954": AreaCodeInfo("FL", "Florida", "America/New_York"),
    # Florida Panhandle — state=FL but physically in Central Time
    "850": AreaCodeInfo("FL", "Florida", "America/Chicago"),

    # Georgia
    "229": AreaCodeInfo("GA", "Georgia", "America/New_York"),
    "404": AreaCodeInfo("GA", "Georgia", "America/New_York"),
    "470": AreaCodeInfo("GA", "Georgia", "America/New_York"),
    "478": AreaCodeInfo("GA", "Georgia", "America/New_York"),
    "678": AreaCodeInfo("GA", "Georgia", "America/New_York"),
    "706": AreaCodeInfo("GA", "Georgia", "America/New_York"),
    "762": AreaCodeInfo("GA", "Georgia", "America/New_York"),
    "770": AreaCodeInfo("GA", "Georgia", "America/New_York"),
    "912": AreaCodeInfo("GA", "Georgia", "America/New_York"),
    "943": AreaCodeInfo("GA", "Georgia", "America/New_York"),

    # Indiana (mostly ET since 2006; NW corner 219 is CT — see below)
    "260": AreaCodeInfo("IN", "Indiana", "America/New_York"),
    "317": AreaCodeInfo("IN", "Indiana", "America/New_York"),
    "463": AreaCodeInfo("IN", "Indiana", "America/New_York"),
    "574": AreaCodeInfo("IN", "Indiana", "America/New_York"),
    "765": AreaCodeInfo("IN", "Indiana", "America/New_York"),
    "812": AreaCodeInfo("IN", "Indiana", "America/New_York"),
    "930": AreaCodeInfo("IN", "Indiana", "America/New_York"),

    # Kentucky Eastern
    "502": AreaCodeInfo("KY", "Kentucky", "America/New_York"),
    "606": AreaCodeInfo("KY", "Kentucky", "America/New_York"),
    "859": AreaCodeInfo("KY", "Kentucky", "America/New_York"),

    # Maine
    "207": AreaCodeInfo("ME", "Maine", "America/New_York"),

    # Maryland
    "240": AreaCodeInfo("MD", "Maryland", "America/New_York"),
    "301": AreaCodeInfo("MD", "Maryland", "America/New_York"),
    "410": AreaCodeInfo("MD", "Maryland", "America/New_York"),
    "443": AreaCodeInfo("MD", "Maryland", "America/New_York"),
    "667": AreaCodeInfo("MD", "Maryland", "America/New_York"),

    # Massachusetts
    "339": AreaCodeInfo("MA", "Massachusetts", "America/New_York"),
    "351": AreaCodeInfo("MA", "Massachusetts", "America/New_York"),
    "413": AreaCodeInfo("MA", "Massachusetts", "America/New_York"),
    "508": AreaCodeInfo("MA", "Massachusetts", "America/New_York"),
    "617": AreaCodeInfo("MA", "Massachusetts", "America/New_York"),
    "774": AreaCodeInfo("MA", "Massachusetts", "America/New_York"),
    "781": AreaCodeInfo("MA", "Massachusetts", "America/New_York"),
    "857": AreaCodeInfo("MA", "Massachusetts", "America/New_York"),
    "978": AreaCodeInfo("MA", "Massachusetts", "America/New_York"),

    # Michigan
    "231": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "248": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "269": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "313": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "517": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "586": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "616": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "734": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "810": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "906": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "947": AreaCodeInfo("MI", "Michigan", "America/New_York"),
    "989": AreaCodeInfo("MI", "Michigan", "America/New_York"),

    # New Hampshire
    "603": AreaCodeInfo("NH", "New Hampshire", "America/New_York"),

    # New Jersey
    "201": AreaCodeInfo("NJ", "New Jersey", "America/New_York"),
    "551": AreaCodeInfo("NJ", "New Jersey", "America/New_York"),
    "609": AreaCodeInfo("NJ", "New Jersey", "America/New_York"),
    "732": AreaCodeInfo("NJ", "New Jersey", "America/New_York"),
    "848": AreaCodeInfo("NJ", "New Jersey", "America/New_York"),
    "856": AreaCodeInfo("NJ", "New Jersey", "America/New_York"),
    "862": AreaCodeInfo("NJ", "New Jersey", "America/New_York"),
    "908": AreaCodeInfo("NJ", "New Jersey", "America/New_York"),
    "973": AreaCodeInfo("NJ", "New Jersey", "America/New_York"),

    # New York
    "212": AreaCodeInfo("NY", "New York", "America/New_York"),
    "315": AreaCodeInfo("NY", "New York", "America/New_York"),
    "332": AreaCodeInfo("NY", "New York", "America/New_York"),
    "347": AreaCodeInfo("NY", "New York", "America/New_York"),
    "516": AreaCodeInfo("NY", "New York", "America/New_York"),
    "518": AreaCodeInfo("NY", "New York", "America/New_York"),
    "585": AreaCodeInfo("NY", "New York", "America/New_York"),
    "607": AreaCodeInfo("NY", "New York", "America/New_York"),
    "631": AreaCodeInfo("NY", "New York", "America/New_York"),
    "646": AreaCodeInfo("NY", "New York", "America/New_York"),
    "680": AreaCodeInfo("NY", "New York", "America/New_York"),
    "716": AreaCodeInfo("NY", "New York", "America/New_York"),
    "718": AreaCodeInfo("NY", "New York", "America/New_York"),
    "838": AreaCodeInfo("NY", "New York", "America/New_York"),
    "845": AreaCodeInfo("NY", "New York", "America/New_York"),
    "914": AreaCodeInfo("NY", "New York", "America/New_York"),
    "917": AreaCodeInfo("NY", "New York", "America/New_York"),
    "929": AreaCodeInfo("NY", "New York", "America/New_York"),
    "934": AreaCodeInfo("NY", "New York", "America/New_York"),

    # North Carolina
    "252": AreaCodeInfo("NC", "North Carolina", "America/New_York"),
    "336": AreaCodeInfo("NC", "North Carolina", "America/New_York"),
    "704": AreaCodeInfo("NC", "North Carolina", "America/New_York"),
    "743": AreaCodeInfo("NC", "North Carolina", "America/New_York"),
    "828": AreaCodeInfo("NC", "North Carolina", "America/New_York"),
    "910": AreaCodeInfo("NC", "North Carolina", "America/New_York"),
    "919": AreaCodeInfo("NC", "North Carolina", "America/New_York"),
    "980": AreaCodeInfo("NC", "North Carolina", "America/New_York"),
    "984": AreaCodeInfo("NC", "North Carolina", "America/New_York"),

    # Ohio
    "216": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "220": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "234": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "283": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "330": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "380": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "419": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "440": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "513": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "567": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "614": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "740": AreaCodeInfo("OH", "Ohio", "America/New_York"),
    "937": AreaCodeInfo("OH", "Ohio", "America/New_York"),

    # Pennsylvania
    "215": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "223": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "267": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "272": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "412": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "445": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "484": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "570": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "610": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "717": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "724": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "814": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "835": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),
    "878": AreaCodeInfo("PA", "Pennsylvania", "America/New_York"),

    # Rhode Island
    "401": AreaCodeInfo("RI", "Rhode Island", "America/New_York"),

    # South Carolina
    "803": AreaCodeInfo("SC", "South Carolina", "America/New_York"),
    "839": AreaCodeInfo("SC", "South Carolina", "America/New_York"),
    "843": AreaCodeInfo("SC", "South Carolina", "America/New_York"),
    "854": AreaCodeInfo("SC", "South Carolina", "America/New_York"),
    "864": AreaCodeInfo("SC", "South Carolina", "America/New_York"),

    # Tennessee Eastern (Knoxville / Tri-Cities)
    "423": AreaCodeInfo("TN", "Tennessee", "America/New_York"),
    "865": AreaCodeInfo("TN", "Tennessee", "America/New_York"),

    # Virginia
    "276": AreaCodeInfo("VA", "Virginia", "America/New_York"),
    "434": AreaCodeInfo("VA", "Virginia", "America/New_York"),
    "540": AreaCodeInfo("VA", "Virginia", "America/New_York"),
    "571": AreaCodeInfo("VA", "Virginia", "America/New_York"),
    "703": AreaCodeInfo("VA", "Virginia", "America/New_York"),
    "757": AreaCodeInfo("VA", "Virginia", "America/New_York"),
    "804": AreaCodeInfo("VA", "Virginia", "America/New_York"),

    # Vermont
    "802": AreaCodeInfo("VT", "Vermont", "America/New_York"),

    # West Virginia
    "304": AreaCodeInfo("WV", "West Virginia", "America/New_York"),
    "681": AreaCodeInfo("WV", "West Virginia", "America/New_York"),

    # ─── CENTRAL TIME  (America/Chicago) ─────────────────────────────────────

    # Alabama
    "205": AreaCodeInfo("AL", "Alabama", "America/Chicago"),
    "251": AreaCodeInfo("AL", "Alabama", "America/Chicago"),
    "256": AreaCodeInfo("AL", "Alabama", "America/Chicago"),
    "334": AreaCodeInfo("AL", "Alabama", "America/Chicago"),
    "938": AreaCodeInfo("AL", "Alabama", "America/Chicago"),

    # Arkansas
    "479": AreaCodeInfo("AR", "Arkansas", "America/Chicago"),
    "501": AreaCodeInfo("AR", "Arkansas", "America/Chicago"),
    "870": AreaCodeInfo("AR", "Arkansas", "America/Chicago"),

    # Illinois
    "217": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "224": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "309": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "312": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "331": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "447": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "464": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "618": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "630": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "708": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "773": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "779": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "815": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "847": AreaCodeInfo("IL", "Illinois", "America/Chicago"),
    "872": AreaCodeInfo("IL", "Illinois", "America/Chicago"),

    # Indiana NW corner (Gary / Hammond metro — Central Time)
    "219": AreaCodeInfo("IN", "Indiana", "America/Chicago"),

    # Iowa
    "319": AreaCodeInfo("IA", "Iowa", "America/Chicago"),
    "515": AreaCodeInfo("IA", "Iowa", "America/Chicago"),
    "563": AreaCodeInfo("IA", "Iowa", "America/Chicago"),
    "641": AreaCodeInfo("IA", "Iowa", "America/Chicago"),
    "712": AreaCodeInfo("IA", "Iowa", "America/Chicago"),

    # Kansas
    "316": AreaCodeInfo("KS", "Kansas", "America/Chicago"),
    "620": AreaCodeInfo("KS", "Kansas", "America/Chicago"),
    "785": AreaCodeInfo("KS", "Kansas", "America/Chicago"),
    "913": AreaCodeInfo("KS", "Kansas", "America/Chicago"),

    # Kentucky Western
    "270": AreaCodeInfo("KY", "Kentucky", "America/Chicago"),
    "364": AreaCodeInfo("KY", "Kentucky", "America/Chicago"),

    # Louisiana
    "225": AreaCodeInfo("LA", "Louisiana", "America/Chicago"),
    "318": AreaCodeInfo("LA", "Louisiana", "America/Chicago"),
    "337": AreaCodeInfo("LA", "Louisiana", "America/Chicago"),
    "504": AreaCodeInfo("LA", "Louisiana", "America/Chicago"),
    "985": AreaCodeInfo("LA", "Louisiana", "America/Chicago"),

    # Minnesota
    "218": AreaCodeInfo("MN", "Minnesota", "America/Chicago"),
    "320": AreaCodeInfo("MN", "Minnesota", "America/Chicago"),
    "507": AreaCodeInfo("MN", "Minnesota", "America/Chicago"),
    "612": AreaCodeInfo("MN", "Minnesota", "America/Chicago"),
    "651": AreaCodeInfo("MN", "Minnesota", "America/Chicago"),
    "763": AreaCodeInfo("MN", "Minnesota", "America/Chicago"),
    "952": AreaCodeInfo("MN", "Minnesota", "America/Chicago"),

    # Mississippi
    "228": AreaCodeInfo("MS", "Mississippi", "America/Chicago"),
    "601": AreaCodeInfo("MS", "Mississippi", "America/Chicago"),
    "662": AreaCodeInfo("MS", "Mississippi", "America/Chicago"),
    "769": AreaCodeInfo("MS", "Mississippi", "America/Chicago"),

    # Missouri
    "314": AreaCodeInfo("MO", "Missouri", "America/Chicago"),
    "417": AreaCodeInfo("MO", "Missouri", "America/Chicago"),
    "573": AreaCodeInfo("MO", "Missouri", "America/Chicago"),
    "636": AreaCodeInfo("MO", "Missouri", "America/Chicago"),
    "660": AreaCodeInfo("MO", "Missouri", "America/Chicago"),
    "816": AreaCodeInfo("MO", "Missouri", "America/Chicago"),

    # Nebraska
    "308": AreaCodeInfo("NE", "Nebraska", "America/Chicago"),
    "402": AreaCodeInfo("NE", "Nebraska", "America/Chicago"),
    "531": AreaCodeInfo("NE", "Nebraska", "America/Chicago"),

    # North Dakota (population center CT; western edge MT — CT used as dominant)
    "701": AreaCodeInfo("ND", "North Dakota", "America/Chicago"),

    # Oklahoma
    "405": AreaCodeInfo("OK", "Oklahoma", "America/Chicago"),
    "539": AreaCodeInfo("OK", "Oklahoma", "America/Chicago"),
    "580": AreaCodeInfo("OK", "Oklahoma", "America/Chicago"),
    "918": AreaCodeInfo("OK", "Oklahoma", "America/Chicago"),

    # South Dakota (CT dominant; Rapid City area is MT — 605 mapped to CT)
    "605": AreaCodeInfo("SD", "South Dakota", "America/Chicago"),

    # Tennessee Central/West (Nashville, Memphis)
    "615": AreaCodeInfo("TN", "Tennessee", "America/Chicago"),
    "629": AreaCodeInfo("TN", "Tennessee", "America/Chicago"),
    "731": AreaCodeInfo("TN", "Tennessee", "America/Chicago"),
    "901": AreaCodeInfo("TN", "Tennessee", "America/Chicago"),
    "931": AreaCodeInfo("TN", "Tennessee", "America/Chicago"),

    # Texas — Central (all codes except El Paso 915)
    "210": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "214": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "254": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "281": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "325": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "346": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "361": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "409": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "430": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "432": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "469": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "512": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "682": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "713": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "726": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "737": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "806": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "817": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "830": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "832": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "903": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "936": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "940": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "945": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "956": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "972": AreaCodeInfo("TX", "Texas", "America/Chicago"),
    "979": AreaCodeInfo("TX", "Texas", "America/Chicago"),

    # Wisconsin
    "262": AreaCodeInfo("WI", "Wisconsin", "America/Chicago"),
    "414": AreaCodeInfo("WI", "Wisconsin", "America/Chicago"),
    "534": AreaCodeInfo("WI", "Wisconsin", "America/Chicago"),
    "608": AreaCodeInfo("WI", "Wisconsin", "America/Chicago"),
    "715": AreaCodeInfo("WI", "Wisconsin", "America/Chicago"),
    "920": AreaCodeInfo("WI", "Wisconsin", "America/Chicago"),

    # ─── MOUNTAIN TIME — with DST  (America/Denver) ──────────────────────────

    # Colorado
    "303": AreaCodeInfo("CO", "Colorado", "America/Denver"),
    "719": AreaCodeInfo("CO", "Colorado", "America/Denver"),
    "720": AreaCodeInfo("CO", "Colorado", "America/Denver"),
    "970": AreaCodeInfo("CO", "Colorado", "America/Denver"),

    # Idaho
    "208": AreaCodeInfo("ID", "Idaho", "America/Denver"),
    "986": AreaCodeInfo("ID", "Idaho", "America/Denver"),

    # Montana
    "406": AreaCodeInfo("MT", "Montana", "America/Denver"),

    # New Mexico
    "505": AreaCodeInfo("NM", "New Mexico", "America/Denver"),
    "575": AreaCodeInfo("NM", "New Mexico", "America/Denver"),

    # Texas — El Paso (Mountain Time)
    "915": AreaCodeInfo("TX", "Texas", "America/Denver"),

    # Utah
    "385": AreaCodeInfo("UT", "Utah", "America/Denver"),
    "435": AreaCodeInfo("UT", "Utah", "America/Denver"),
    "801": AreaCodeInfo("UT", "Utah", "America/Denver"),

    # Wyoming
    "307": AreaCodeInfo("WY", "Wyoming", "America/Denver"),

    # ─── MOUNTAIN TIME — NO DST  (America/Phoenix) ───────────────────────────

    # Arizona (Navajo Nation observes DST but uses the same area codes)
    "480": AreaCodeInfo("AZ", "Arizona", "America/Phoenix"),
    "520": AreaCodeInfo("AZ", "Arizona", "America/Phoenix"),
    "602": AreaCodeInfo("AZ", "Arizona", "America/Phoenix"),
    "623": AreaCodeInfo("AZ", "Arizona", "America/Phoenix"),
    "928": AreaCodeInfo("AZ", "Arizona", "America/Phoenix"),

    # ─── PACIFIC TIME  (America/Los_Angeles) ─────────────────────────────────

    # California
    "209": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "213": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "310": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "323": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "341": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "350": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "408": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "415": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "424": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "442": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "510": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "530": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "559": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "562": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "619": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "626": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "628": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "650": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "657": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "661": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "669": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "707": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "714": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "747": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "760": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "764": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "805": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "818": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "820": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "831": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "858": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "909": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "916": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "925": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "949": AreaCodeInfo("CA", "California", "America/Los_Angeles"),
    "951": AreaCodeInfo("CA", "California", "America/Los_Angeles"),

    # Nevada
    "702": AreaCodeInfo("NV", "Nevada", "America/Los_Angeles"),
    "725": AreaCodeInfo("NV", "Nevada", "America/Los_Angeles"),
    "775": AreaCodeInfo("NV", "Nevada", "America/Los_Angeles"),

    # Oregon
    "458": AreaCodeInfo("OR", "Oregon", "America/Los_Angeles"),
    "503": AreaCodeInfo("OR", "Oregon", "America/Los_Angeles"),
    "541": AreaCodeInfo("OR", "Oregon", "America/Los_Angeles"),
    "971": AreaCodeInfo("OR", "Oregon", "America/Los_Angeles"),

    # Washington State
    "206": AreaCodeInfo("WA", "Washington", "America/Los_Angeles"),
    "253": AreaCodeInfo("WA", "Washington", "America/Los_Angeles"),
    "360": AreaCodeInfo("WA", "Washington", "America/Los_Angeles"),
    "425": AreaCodeInfo("WA", "Washington", "America/Los_Angeles"),
    "509": AreaCodeInfo("WA", "Washington", "America/Los_Angeles"),
    "564": AreaCodeInfo("WA", "Washington", "America/Los_Angeles"),

    # ─── ALASKA  (America/Anchorage) ─────────────────────────────────────────
    "907": AreaCodeInfo("AK", "Alaska", "America/Anchorage"),

    # ─── HAWAII  (Pacific/Honolulu — no DST) ─────────────────────────────────
    "808": AreaCodeInfo("HI", "Hawaii", "Pacific/Honolulu"),

    # ─── US TERRITORIES ──────────────────────────────────────────────────────
    "787": AreaCodeInfo("PR", "Puerto Rico", "America/Puerto_Rico"),
    "939": AreaCodeInfo("PR", "Puerto Rico", "America/Puerto_Rico"),
    "340": AreaCodeInfo("VI", "U.S. Virgin Islands", "America/St_Thomas"),
    "671": AreaCodeInfo("GU", "Guam", "Pacific/Guam"),
    "670": AreaCodeInfo("MP", "Northern Mariana Islands", "Pacific/Saipan"),
    "684": AreaCodeInfo("AS", "American Samoa", "Pacific/Pago_Pago"),
}


def get_area_code_info(area_code: str) -> AreaCodeInfo:
    """Return routing info for a 3-digit area code, or FEDERAL_FALLBACK."""
    return AREA_CODE_MAP.get(area_code.strip(), FEDERAL_FALLBACK)


def extract_area_code(phone_number: str) -> str | None:
    """
    Parse a phone number in E.164 (+1XXXXXXXXXX) or 10-digit format and return
    the 3-digit NANPA area code string, or None if the format is unrecognisable.
    """
    digits = "".join(ch for ch in phone_number if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:4]
    if len(digits) == 10:
        return digits[:3]
    return None


def resolve_phone(phone_number: str) -> AreaCodeInfo:
    """
    Full resolution: phone number string → AreaCodeInfo.
    Returns FEDERAL_FALLBACK when the number cannot be parsed.
    """
    area_code = extract_area_code(phone_number)
    if area_code is None:
        return FEDERAL_FALLBACK
    return get_area_code_info(area_code)
