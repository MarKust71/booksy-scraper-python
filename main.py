# %%
# INIT
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

from selenium import webdriver
driver = webdriver.Chrome()


# %%
BOOKSY_PAGE_URL = "https://booksy.com/pl-pl/s/salon-kosmetyczny/32675_zoliborz?businessesPage="
driver.get(f"{BOOKSY_PAGE_URL}1")


# %%
# pobranie źródła strony i sparsowanie BeautifulSoup
from bs4 import BeautifulSoup


def number_of_pages(soup: BeautifulSoup):
    ul = soup.find("ul", class_="purify_-3qcdAGB2X7TYFBS7epuOA==")
    if ul:
        li_list = ul.find_all("li")
        if len(li_list) >= 2:
            target_li = li_list[-2]  # przedostatni <li>
            a_tag = target_li.find("a")
            if a_tag:
                text = a_tag.get_text(strip=True)

                return int(text)
            else:
                print("[number_of_pages]: Brak <a> w przedostatnim <li>")
        else:
            print("[number_of_pages]: Za mało elementów <li>")
    else:
        print("[number_of_pages]: Nie znaleziono <ul>")


def find_connections_on_page(soup: BeautifulSoup):
    CLASS = "purify_9grRfCWyq-PDUgGR34P0cQ=="

    connections = soup.find_all("div", class_=CLASS)
    number_of_connections = len(connections)
    print(f"{number_of_connections} connections found on page.")

    return connections


page_source = driver.page_source
soup = BeautifulSoup(page_source, "html.parser")
number_of_pages = number_of_pages(soup)
print(f"Liczba stron: {number_of_pages}")


# %%
from pprint import pprint


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

    street = (head
              .replace('ul ', "")
              .replace('ul.', "")
              .replace('ulica ', "")
              )

    parts = street.split(', ')
    if len(parts) == 2:
        street, local = parts
        result["local"] = (local
                           .replace("Lok", "")
                           .replace("lok", "")
                           .strip(". ")
                           )

    parts = street.split()
    if len(parts) > 1:
        b = parts[-1]
        if re.match(r'^\d+[A-Z]?$', b):
            street = ' '.join(parts[:-1])
            result["building"] = b

    parts = street.split()
    if len(parts) > 1:
        b = parts[-1]
        if re.match(r'^\d+[A-Z]?\/\d+[A-Z]?$', b):
            street = ' '.join(parts[:-1])
            result["building"] = b

    result["street"] = street if street else None

    if not result["building"] and result["local"]:
        result["building"] = result["local"]
        result["local"] = None

    return result


CLASS_LOCATION = "purify_prm7MfDXczhTZvcY5KwOuA== purify_Sardy6hfiet162IZ2pYFPA== purify_m9mNOPjpHD0tNTW6GC+hEw=="
BOOKSY_URL = "https://booksy.com"

connections_list = []
# number_of_pages = 1 # mock
for page_number in range(1, number_of_pages + 1):
    print(f"Strona {page_number}")
    driver.get(f"{BOOKSY_PAGE_URL}{page_number}")

    # print("Pobieram źródło strony i parsuję BeautifulSoup...")
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")

    connections = find_connections_on_page(soup)

    for connection in connections:
        connection_dict = {}

        business_promoted = False
        business_name_text = None
        business_location = None
        business_location_raw = None
        business_booksy_url = None

        try:
            business_name = connection.find("h2", attrs={"data-testid": "business-name"})
            business_name_text = business_name.text.strip()
            business_booksy_url = business_name.find_parent("a")["href"]
            business_location = get_deepest_div_text(connection.find("div", class_=CLASS_LOCATION))
        except Exception as e:
            continue

        connection_dict.update({
            "business_name": business_name_text,
            "business_promoted": business_promoted,
            "business_location_raw": business_location,
            "business_location": parse_business_location(business_location) if business_location else None,
            "business_booksy_url": f'{BOOKSY_URL}{business_booksy_url}' if business_booksy_url else None,
        })

        connections_list.append(connection_dict)


# %%
import os, psycopg2

from dotenv import load_dotenv
load_dotenv(override=True)


# parametrów połączenia nie trzeba wczytywać ponownie, .env jest już załadowane :contentReference[oaicite:1]{index=1}
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", 5432)
DB_NAME     = os.getenv("DB_NAME", "booksy_scraper")
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

def db_add_connections(connections_list):
    print(f"Liczba połączeń: {len(connections_list)}")

    # ——— ZAPIS DO BAZY POSTGRES ———
    try:
        print("Zapisywanie do bazy PostgreSQL...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=30,        # zwiększony timeout
            gssencmode='disable',      # wyłączenie GSSAPI
            sslmode='prefer',          # elastyczne podejście do SSL
            client_encoding='UTF8'
        )
        print(f"  PostgreSQL connection: {conn}")

        cur = conn.cursor()
        print(f"  PostgreSQL cursor: {cur}")

        ###############################################
        ## tworzymy tabelę (jeśli nie istnieje) z dodatkowymi polami na zdjęcie i kontakt_info
        print("  Tworzenie tabeli...")
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS connections (
                                                                id                          SERIAL PRIMARY KEY,
                                                                booksy_business_name        TEXT,
                                                                booksy_url                  TEXT UNIQUE,
                                                                is_promoted                 BOOLEAN,
                                                                location_raw                TEXT,
                                                                location_postal_code        TEXT,
                                                                location_city               TEXT,
                                                                location_district           TEXT,
                                                                location_street             TEXT,
                                                                location_building           TEXT,
                                                                location_local              TEXT,
                                                                registered_business_name    TEXT,
                                                                phone                       TEXT,
                                                                email                       TEXT,
                                                                created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """)
        conn.commit()
        print("  Tworzenie tabeli zakończone.")

        ## dodajemy funkcję do aktualizacji updated_at
        print("  Dodawanie funkcji do aktualizacji updated_at...")
        cur.execute("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
        """)
        conn.commit()
        print("  Dodawanie funkcji zakończone.")

        ## dodajemy trigger do tabeli connections
        print("  Dodawanie triggera do tabeli connections...")
        cur.execute("""
                    DROP TRIGGER IF EXISTS set_updated_at ON connections;
                    CREATE TRIGGER set_updated_at
                    BEFORE UPDATE ON connections
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
        """)
        conn.commit()
        print("  Dodawanie triggera zakończone.")


        ## ——— Dodaj unikalny indeks na contact_info.profile ———
        print("  Dodawanie unikalnego indeksu na contact_info.profile...")
        cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS unique_booksy_url
                        ON connections (booksy_url);
                    """)
        conn.commit()
        print("  Dodawanie unikalnego indeksu zakończone.")
        print("Tworzenie tabeli zakończone.")
        ## koniec tworzenia tabeli
        ###############################################


        cur.execute("SELECT booksy_url FROM connections;")
        seen_connections = {row[0] for row in cur.fetchall() if row[0]}
        print(f"Liczba unikalnych połączeń: {len(seen_connections)}")

        ## dodawanie rekordów do tabeli
        number = 0
        for c in connections_list:
            pprint(c)
            cur.execute("""
                        INSERT INTO connections
                        (booksy_business_name, booksy_url, is_promoted, location_raw,
                         location_postal_code, location_city, location_district, location_street, location_building,
                         location_local, registered_business_name, phone, email)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (booksy_url) DO NOTHING;
                        """, (
                            c["business_name"],
                            c["business_booksy_url"],
                            False,
                            c["business_location_raw"],
                            c["business_location"]["postal_code"],
                            c["business_location"]["city"],
                            c["business_location"]["district"],
                            c["business_location"]["street"],
                            c["business_location"]["building"],
                            c["business_location"]["local"],
                            "",
                            "",
                            ""
                        ))
            conn.commit()
            number += 1
            print(number)

        ## koniec dodawania rekordów

        cur.execute("SELECT booksy_url FROM connections;")
        seen_connections = {row[0] for row in cur.fetchall() if row[0]}

        # zamknięcie połączenia
        cur.close()

    except psycopg2.OperationalError as e:
        print(f"Błąd połączenia z bazą danych: {e}")
        raise
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()
            print("PostgreSQL connection closed.")
    # ——— KONIEC ZAPISU ———


    return seen_connections

seen_connections = db_add_connections(connections_list)
print(f"Liczba unikalnych połączeń: {len(seen_connections)}")
