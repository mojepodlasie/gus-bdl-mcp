"""Serwer MCP dla Banku Danych Lokalnych GUS (BDL API v1).

Dokumentacja API: https://api.stat.gov.pl/Home/BdlApi
Transport: streamable HTTP, endpoint /mcp
"""

import asyncio
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

BDL_BASE_URL = "https://bdl.stat.gov.pl/api/v1"
CLIENT_ID = os.environ.get("GUS_BDL_CLIENT_ID", "").strip()
PORT = int(os.environ.get("PORT", "8000"))
TIMEOUT = httpx.Timeout(float(os.environ.get("GUS_BDL_TIMEOUT", "60")), connect=15.0)
MAX_ATTEMPTS = 2
RETRY_STATUSES = {429, 500, 502, 503, 504}

mcp = FastMCP(
    "gus-bdl",
    instructions=(
        "Narzędzia do Banku Danych Lokalnych GUS. Typowy przebieg: "
        "1) search_subjects lub search_variables, aby znaleźć ID zmiennej; "
        "2) search_units, aby znaleźć ID jednostki terytorialnej; "
        "3) get_data_by_unit lub get_data_by_variable, aby pobrać wartości. "
        "Poziomy jednostek (unit_level): 0 Polska, 1 makroregion, 2 województwo, "
        "3 region, 4 podregion, 5 powiat, 6 gmina."
    ),
    host="0.0.0.0",
    port=PORT,
    stateless_http=True,
    json_response=True,
)


async def bdl_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Wywołuje BDL API i zwraca odpowiedź JSON albo opis błędu."""
    query: dict[str, Any] = {"format": "json", "lang": "pl"}
    for key, value in (params or {}).items():
        if value is not None and value != "" and value != []:
            query[key] = value
    headers = {"Accept": "application/json", "User-Agent": "gus-bdl-mcp/1.1"}
    if CLIENT_ID:
        headers["X-ClientId"] = CLIENT_ID

    last_error = ""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = await client.get(
                    f"{BDL_BASE_URL}{path}", params=query, headers=headers
                )
            except httpx.TimeoutException as exc:
                last_error = f"Przekroczono czas oczekiwania na GUS ({type(exc).__name__})"
            except httpx.HTTPError as exc:
                last_error = f"Błąd połączenia z GUS ({type(exc).__name__}): {exc}"
            else:
                if response.status_code == 200:
                    return response.json()
                last_error = f"BDL API zwróciło status {response.status_code}"
                if response.status_code not in RETRY_STATUSES:
                    return {"error": last_error, "details": response.text[:1000]}
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(2 * attempt)

    hint = (
        ""
        if CLIENT_ID
        else " Wskazówka: ustaw zmienną GUS_BDL_CLIENT_ID (klucz z https://api.stat.gov.pl/Home/BdlApi), "
        "aby korzystać z własnego limitu zapytań."
    )
    return {"error": f"{last_error} po {MAX_ATTEMPTS} próbach.{hint}", "path": path}


@mcp.tool()
async def search_subjects(name: str, page: int = 0, page_size: int = 20) -> dict[str, Any]:
    """Wyszukuje tematy (dziedziny) BDL po nazwie, np. 'ludność', 'bezrobocie'."""
    return await bdl_get(
        "/subjects/search", {"name": name, "page": page, "page-size": page_size}
    )


@mcp.tool()
async def get_subject(subject_id: str) -> dict[str, Any]:
    """Zwraca szczegóły tematu BDL (np. 'P2137') wraz z podtematami."""
    return await bdl_get(f"/subjects/{subject_id}")


@mcp.tool()
async def search_variables(
    name: str = "",
    subject_id: str = "",
    page: int = 0,
    page_size: int = 20,
) -> dict[str, Any]:
    """Wyszukuje zmienne BDL po nazwie lub listuje zmienne w danym temacie (subject_id)."""
    if subject_id and not name:
        return await bdl_get(
            "/variables", {"subject-id": subject_id, "page": page, "page-size": page_size}
        )
    return await bdl_get(
        "/variables/search",
        {"name": name, "subject-id": subject_id, "page": page, "page-size": page_size},
    )


@mcp.tool()
async def search_units(
    name: str,
    level: int | None = None,
    page: int = 0,
    page_size: int = 20,
) -> dict[str, Any]:
    """Wyszukuje jednostki terytorialne po nazwie, np. 'Grajewo'. level: 0-6 (2 = województwo, 5 = powiat, 6 = gmina)."""
    return await bdl_get(
        "/units/search",
        {"name": name, "level": level, "page": page, "page-size": page_size},
    )


@mcp.tool()
async def get_data_by_unit(
    unit_id: str,
    variable_ids: list[int],
    years: list[int] | None = None,
) -> dict[str, Any]:
    """Pobiera wartości wybranych zmiennych (variable_ids) dla jednej jednostki terytorialnej (unit_id)."""
    return await bdl_get(
        f"/data/by-unit/{unit_id}", {"var-id": variable_ids, "year": years or []}
    )


@mcp.tool()
async def get_data_by_variable(
    variable_id: int,
    unit_level: int | None = None,
    parent_id: str = "",
    years: list[int] | None = None,
    page: int = 0,
    page_size: int = 100,
) -> dict[str, Any]:
    """Pobiera wartości jednej zmiennej dla wielu jednostek, np. wszystkich powiatów (unit_level=5) w województwie (parent_id)."""
    return await bdl_get(
        f"/data/by-variable/{variable_id}",
        {
            "unit-level": unit_level,
            "unit-parent-id": parent_id,
            "year": years or [],
            "page": page,
            "page-size": page_size,
        },
    )


@mcp.tool()
async def get_measures() -> dict[str, Any]:
    """Zwraca listę jednostek miary używanych w BDL (np. osoba, %, zł)."""
    return await bdl_get("/measures", {"page-size": 100})


@mcp.custom_route("/", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Prosty test działania usługi (np. dla Render)."""
    return JSONResponse(
        {"status": "ok", "service": "gus-bdl-mcp", "mcp_endpoint": "/mcp", "client_id_set": bool(CLIENT_ID)}
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
