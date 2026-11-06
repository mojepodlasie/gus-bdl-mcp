# gus-bdl-mcp

Serwer MCP (Model Context Protocol) udostępniający dane z **Banku Danych Lokalnych GUS** (BDL API v1) asystentom AI, np. Claude.

Projekt: Fundacja „MOJE PODL@SIE. NOWOCZESNE, KREATYWNE, TWÓRCZE” — https://mojepodlasie.eu

## Narzędzia

| Narzędzie | Opis |
|---|---|
| `search_subjects` | Wyszukiwanie tematów BDL po nazwie |
| `get_subject` | Szczegóły tematu i jego podtematy |
| `search_variables` | Wyszukiwanie zmiennych (wskaźników) |
| `search_units` | Wyszukiwanie jednostek terytorialnych (gmina, powiat, województwo) |
| `get_data_by_unit` | Wartości zmiennych dla jednej jednostki |
| `get_data_by_variable` | Wartości jednej zmiennej dla wielu jednostek |
| `get_measures` | Jednostki miary |

## Uruchomienie lokalne

```bash
pip install -r requirements.txt
python server.py
```

Endpoint MCP: `http://localhost:8000/mcp`

## Wdrożenie (Render)

Web Service, środowisko Docker, plan Free. Endpoint: `https://<nazwa-usługi>.onrender.com/mcp`

## Zmienne środowiskowe

- `GUS_BDL_CLIENT_ID` (opcjonalnie) — klucz API z https://api.stat.gov.pl/Home/BdlApi. Bez klucza obowiązują niższe limity zapytań.
- `PORT` — ustawiany automatycznie przez Render.

## Podłączenie do Claude

Ustawienia → Konektory → Dodaj własny konektor → adres `https://<nazwa-usługi>.onrender.com/mcp`.

Uwaga: na planie Free usługa usypia po ok. 15 minutach bezczynności; pierwsze zapytanie po przerwie może trwać do minuty.
