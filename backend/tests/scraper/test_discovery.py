"""Tests for AWS directory API discovery (S1.1)."""

import json
from typing import Any

import httpx
import pytest

from app.core.errors import ScrapeError
from app.scraper.discovery import ArchitectureUrlDiscoverer, DiscoveredArchitecture

API_URL = "https://aws.amazon.com/api/dirs/items/search"


def directory_item(title: str, url: str) -> dict[str, Any]:
    return {"item": {"additionalFields": {"headline": title, "headlineUrl": url}}}


def make_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


async def test_discover_pages_through_api_until_limit() -> None:
    def item_for(index: int) -> dict[str, Any]:
        return directory_item(f"Arch {index}", f"https://aws.amazon.com/solutions/arch-{index}/")

    pages = {
        "0": [item_for(i) for i in range(3)],
        "1": [item_for(i) for i in range(3, 6)],
    }

    def serve(request: httpx.Request) -> httpx.Response:
        page = request.url.params["page"]
        return httpx.Response(200, json={"items": pages.get(page, [])})

    async with make_client(httpx.MockTransport(serve)) as client:
        results = await ArchitectureUrlDiscoverer(client, page_size=3).discover(limit=5)

    assert len(results) == 5
    assert results[0] == DiscoveredArchitecture(
        title="Arch 0", url="https://aws.amazon.com/solutions/arch-0"
    )
    assert results[4].title == "Arch 4"


async def test_discover_strips_tracking_params_and_deduplicates() -> None:
    items = [
        directory_item(
            "Waiting Room", "https://aws.amazon.com/solutions/waiting-room/?did=sl_card&trk=sl_card"
        ),
        directory_item("Waiting Room (dup)", "https://aws.amazon.com/solutions/waiting-room/"),
        directory_item("Other", "https://aws.amazon.com/solutions/other/"),
    ]

    def serve(request: httpx.Request) -> httpx.Response:
        page = request.url.params["page"]
        return httpx.Response(200, json={"items": items if page == "0" else []})

    async with make_client(httpx.MockTransport(serve)) as client:
        results = await ArchitectureUrlDiscoverer(client).discover(limit=10)

    assert [item.url for item in results] == [
        "https://aws.amazon.com/solutions/waiting-room",
        "https://aws.amazon.com/solutions/other",
    ]


async def test_discover_skips_items_without_title_or_url() -> None:
    items = [
        {"item": {"additionalFields": {"headline": "No URL here"}}},
        {"item": {}},
        directory_item("Valid", "https://aws.amazon.com/solutions/valid/"),
    ]

    def serve(request: httpx.Request) -> httpx.Response:
        page = request.url.params["page"]
        return httpx.Response(200, json={"items": items if page == "0" else []})

    async with make_client(httpx.MockTransport(serve)) as client:
        results = await ArchitectureUrlDiscoverer(client).discover(limit=10)

    assert results == [
        DiscoveredArchitecture(title="Valid", url="https://aws.amazon.com/solutions/valid")
    ]


async def test_discover_raises_scrape_error_on_malformed_payload() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=json.dumps({"unexpected": True}))
    )
    async with make_client(transport) as client:
        with pytest.raises(ScrapeError):
            await ArchitectureUrlDiscoverer(client).discover(limit=5)
