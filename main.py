# %%
# INIT
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from selenium import webdriver
driver = webdriver.Chrome()

from dotenv import load_dotenv
load_dotenv(override=True)


# %%
BOOKSY_PAGE_URL = "https://booksy.com/pl-pl/s/salon-kosmetyczny/32675_zoliborz?businessesPage=1"
driver.get(BOOKSY_PAGE_URL)


# %%
CLASS = "purify_9grRfCWyq-PDUgGR34P0cQ=="

# pobranie źródła strony i sparsowanie BeautifulSoup
from bs4 import BeautifulSoup
from pprint import pprint

print("****************************")
print("Pobieram źródło strony i parsuję BeautifulSoup...")
page_source = driver.page_source
soup = BeautifulSoup(page_source, "html.parser")
connections = soup.find_all("div", class_=CLASS)
number_of_connections = len(connections)
print("****************************")
print(f"{number_of_connections} connections found on page.")


# %%
def get_deepest_div_text(tag):
    current = tag
    while True:
        children = current.find_all("div", recursive=False)
        if not children:
            break
        current = children[0]

    # usuń teksty z wnętrza <span>, weź tylko tekst bezpośrednio z diva
    texts = [
        t for t in current.find_all(string=True, recursive=True)
        if not t.parent.name == "span"
    ]
    return " ".join(t.strip() for t in texts if t.strip())

def parse_business_location(location_str: str) -> dict[str, str | None]:
    import re

    result: dict[str, str | None] = {
        "street": None,
        "building": None,
        "local": None,
        "postal_code": None,
        "city": None,
        "district": None
    }

    # Najpierw spróbuj wyciągnąć kod pocztowy, miasto i dzielnicę
    pattern_tail = re.search(r"(\d{2}-\d{3}),\s*(Warszawa),\s*([\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ\- ]+)$", location_str)
    if pattern_tail:
        result["postal_code"] = pattern_tail.group(1)
        result["city"] = pattern_tail.group(2)
        result["district"] = pattern_tail.group(3).strip()
        head = location_str[:pattern_tail.start()].strip(", ")
    else:
        head = location_str

    # Wyodrębnij lokal (np. "lok U4", "U07", "lok. 6.1", "lokal 56", "m 103")
    local_pattern = re.search(r"(lok(?:al)?\.?\s*[Uu]?\d+[\/\dA-Za-z\.]*)|([UuMm] ?\d+)", head)
    if local_pattern:
        result["local"] = (local_pattern.group(0)
                           .strip()
                           .replace("lok ", "")
                           .replace("lok. ", "")
                           .replace("lokal ", "")
                           .replace("m ", "")
                           .replace("m. ", ""))
        head = head.replace(local_pattern.group(0), "").strip(", ")

    # Spróbuj zidentyfikować ulicę lub miejscowość + numer
    # Usuń ewentualne nawiasy z dodatkowymi wskazówkami
    head = re.sub(r"\(.*?\)", "", head).strip(", ")

    result["street"] = (head
                        .replace('ul ', "")
                        .replace('ul.', "")
                        .replace('ulica ', "")
                        ) if head else None

    return result

CLASS_LOCATION = "purify_prm7MfDXczhTZvcY5KwOuA== purify_Sardy6hfiet162IZ2pYFPA== purify_m9mNOPjpHD0tNTW6GC+hEw=="
BOOKSY_URL = "https://booksy.com"

connections_list = []
for connection in connections:
    connection_dict = {}

    business_promoted = False
    business_name_div_text = None
    business_name_h2_text = None
    business_location = None
    business_location_raw = None
    business_booksy_url = None

    try:
        business_name_h2 = connection.find("h2", attrs={"data-testid": "business-name"})
        business_name_h2_text = business_name_h2.text.strip()
        business_booksy_url = business_name_h2.find_parent("a")["href"]
        business_location = get_deepest_div_text(connection.find("div", class_=CLASS_LOCATION))
    except Exception as e:
        pass

    connection_dict.update({
        "business_name": business_name_div_text or business_name_h2_text,
        "business_promoted": business_promoted,
        "business_location_raw": business_location,
        "business_location": parse_business_location(business_location) if business_location else None,
        "business_booksy_url": f'{BOOKSY_URL}{business_booksy_url}' if business_booksy_url else None,
    })

    connections_list.append(connection_dict)

    pprint(connection_dict)
    pprint("        ")
