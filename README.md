# Worker Celery do rozproszonego scrapera

Jednostka wykonawcza projektu https://github.com/adi8900/web_scrappper. Wersja badawcza: gałąź `thesis-refinement-2026-11`.

## Uruchomienie na osobnym komputerze

1. Zainstaluj Docker i Docker Compose.
2. `cp .env.example .env`.
3. Ustaw `REDIS_URL=redis://:HASLO@ADRES_MASTER:6379/0`, `SHOP_BASE_URL=http://ADRES_MASTER:8090` i `SHOP_PUBLIC_BASE_URL=http://ADRES_MASTER:8090`.
4. Ustaw unikalne `WORKER_NAME` na każdym komputerze, np. `worker1`, `worker2`, `worker3`.
5. `docker compose up -d --build`.
6. Sprawdź `docker compose logs -f worker`.

Każdy worker konsumuje wspólne kolejki `scraping,catalog`. W zależności od ilości zasobów ustaw `CONCURRENCY=1` albo `2`. Podczas pomiarów należy **utrzymywać stałą współbieżność na worker** i zmieniać wyłącznie liczbę aktywnych maszyn.

Worker potrzebuje połączenia TCP do Redis na porcie 6379 i sklepu testowego na porcie 8090. Używaj prywatnej sieci LAN lub VPN; nie wystawiaj Redis publicznie. Uwierzytelnienie Redis jest wymagane.

## Tryby pozyskiwania danych

- `html`: Playwright (Chromium) pobiera wyrenderowaną stronę; BeautifulSoup analizuje różne selektory HTML trzech sklepów.
- `api`: httpx pobiera dane JSON z endpointu każdego sklepu.

Oba warianty przekazują `product_id`, `listing_id`, nazwę, cenę i specyfikacje. `scrape_catalog` zwraca dodatkowo czas wykonania zadania i liczbę pobranych rekordów.

Projekt nie zawiera integracji z x-kom, Morele ani MediaExpert, a wszystkie ceny sklepów testowych są syntetyczne.
