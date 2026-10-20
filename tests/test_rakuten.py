from datetime import UTC, datetime

import pandas as pd
import pytest
import requests

from svi import build, prices
from svi.config import get_config
from svi.ids import Resolver
from svi.scrapers import rakuten, retailers
from svi.scrapers.rakuten import (
    Credentials,
    RakutenError,
    items_to_observations,
    parse_search_xml,
    scrape_newegg_prices,
    search_keyword,
)
from svi.scrapers.retailers import RetailerSkipped

NOW = datetime(2026, 9, 29, tzinfo=UTC)
CREDS = Credentials("client-id", "client-secret-XYZ", "1234567")

# Product Search response in Rakuten's documented shape. Live items can't be captured until
# the Newegg partnership is approved; the error document below is a real response.
SEARCH_4070 = """<?xml version="1.0" encoding="UTF-8"?>
<result><TotalMatches>5</TotalMatches><TotalPages>1</TotalPages><PageNumber>1</PageNumber>
<item><mid>44583</mid><merchantname>Newegg</merchantname><linkid>1001</linkid>
  <sku>N82E16814137771</sku>
  <productname>MSI Ventus 2X GeForce RTX 4070 12GB GDDR6X Graphics Card</productname>
  <category><primary>Components</primary><secondary>Video Cards</secondary></category>
  <price currency="USD">599.99</price><saleprice currency="USD">549.99</saleprice>
  <linkurl>https://click.linksynergy.com/link?id=abc&amp;offerid=1.1001&amp;type=15</linkurl></item>
<item><mid>44583</mid><sku>N82E16814126600</sku>
  <productname>ASUS TUF Gaming GeForce RTX 4070 Ti SUPER 16GB GDDR6X Graphics Card</productname>
  <price currency="USD">849.99</price><saleprice currency="USD"></saleprice>
  <linkurl>https://click.linksynergy.com/link?id=abc&amp;offerid=1.1002</linkurl></item>
<item><mid>44583</mid><sku>N82E16814932999</sku>
  <productname>Gigabyte GeForce RTX 4070 12GB Open Box Graphics Card</productname>
  <price currency="USD">489.99</price>
  <linkurl>https://click.linksynergy.com/link?id=abc&amp;offerid=1.1003</linkurl></item>
<item><mid>44583</mid><sku>N82E16883000000</sku>
  <productname>Gaming PC Bundle with GeForce RTX 4070 12GB</productname>
  <price currency="USD">1,499.00</price>
  <linkurl>https://click.linksynergy.com/link?id=abc&amp;offerid=1.1004</linkurl></item>
<item><mid>44583</mid><sku>N82E16814500001</sku>
  <productname>Zotac GeForce RTX 4070 Twin Edge 12GB Graphics Card</productname>
  <price currency="CAD">799.00</price>
  <linkurl>https://click.linksynergy.com/link?id=abc&amp;offerid=1.1005</linkurl></item>
</result>"""

NO_MATCHES = (
    "<result><Errors><ErrorID>7186919</ErrorID><ErrorText>No matching products found. "
    "Possible reasons include lack of approval from the specified Advertiser or no active "
    "relationships with any Advertiser.</ErrorText></Errors></result>"
)


def registry(*gpus):
    return pd.DataFrame(
        [dict(gpu_id=g, vendor=v, display_name=d, is_active="true") for g, v, d in gpus]
    )


def test_search_keyword_uses_vendor_prefix():
    assert search_keyword("NVIDIA", "RTX 4070 Ti Super") == "GeForce RTX 4070 Ti Super"
    assert search_keyword("AMD", "RX 9070 XT") == "Radeon RX 9070 XT"


def test_parse_search_xml_items_and_pages():
    items, pages = parse_search_xml(SEARCH_4070)
    assert pages == 1
    assert len(items) == 5
    assert items[0] == {
        "sku": "N82E16814137771",
        "productname": "MSI Ventus 2X GeForce RTX 4070 12GB GDDR6X Graphics Card",
        "price": "599.99",
        "saleprice": "549.99",
        "currency": "USD",
        "linkurl": "https://click.linksynergy.com/link?id=abc&offerid=1.1001&type=15",
    }
    assert items[4]["currency"] == "CAD"


def test_parse_search_xml_no_matches_is_empty():
    assert parse_search_xml(NO_MATCHES) == ([], 0)


def test_parse_search_xml_other_errors_raise():
    with pytest.raises(RakutenError, match="error 42"):
        parse_search_xml(
            "<result><Errors><ErrorID>42</ErrorID><ErrorText>x</ErrorText></Errors></result>"
        )


def test_items_filtered_to_requested_gpu():
    items, _ = parse_search_xml(SEARCH_4070)
    obs, _ = items_to_observations(
        items, "nvidia-rtx-4070", Resolver.from_files(), now=NOW, run_id="t"
    )
    by_sku = {o["sku"]: o for o in obs}
    # 4070 Ti SUPER is a different card, the bundle is filtered, the CAD listing is skipped.
    assert set(by_sku) == {"N82E16814137771", "N82E16814932999"}
    sale = by_sku["N82E16814137771"]
    assert sale["price"] == 549.99  # sale price wins over list price
    assert sale["retailer"] == "newegg"
    assert sale["condition"] == "new"
    assert sale["url"].startswith("https://click.linksynergy.com/")
    assert by_sku["N82E16814932999"]["condition"] == "refurb"  # open box is not new


def test_open_box_is_rejected_by_validation():
    items, _ = parse_search_xml(SEARCH_4070)
    obs, _ = items_to_observations(
        items, "nvidia-rtx-4070", Resolver.from_files(), now=NOW, run_id="t"
    )
    df = prices.validate_observations(
        pd.DataFrame(obs, columns=prices.PRICE_COLUMNS),
        pd.DataFrame(columns=prices.PRICE_COLUMNS),
        get_config().pricing,
        now=NOW,
    )
    assert df.set_index("sku").loc["N82E16814932999", "invalid_reason"] == "not_new"
    assert df.set_index("sku").loc["N82E16814137771", "is_valid"]


def test_missing_credentials_skip_without_network(monkeypatch):
    for var in ("RAKUTEN_CLIENT_ID", "RAKUTEN_CLIENT_SECRET", "RAKUTEN_SID"):
        monkeypatch.delenv(var, raising=False)

    def no_network(*args, **kwargs):
        raise AssertionError("must not call the API without credentials")

    with pytest.raises(RetailerSkipped, match="RAKUTEN_CLIENT_ID"):
        scrape_newegg_prices(
            Resolver.from_files(),
            registry(),
            get_config(),
            run_id="t",
            now=NOW,
            token_fn=no_network,
            status_fn=no_network,
            search_fn=no_network,
        )


@pytest.mark.parametrize("status", ["pending", "none", "declined"])
def test_unapproved_partnership_is_a_skip(status):
    searched = []
    with pytest.raises(RetailerSkipped, match=f"'{status}', not approved yet"):
        scrape_newegg_prices(
            Resolver.from_files(),
            registry(("nvidia-rtx-4070", "NVIDIA", "RTX 4070")),
            get_config(),
            run_id="t",
            now=NOW,
            creds=CREDS,
            token_fn=lambda c: "tok",
            status_fn=lambda t, mid: status,
            search_fn=lambda *a: searched.append(a) or [],
        )
    assert searched == []


@pytest.mark.parametrize("status", ["extended", "active"])
def test_approved_partnership_scrapes_each_active_gpu(status):
    calls = []

    def search(token, keyword, mid):
        calls.append((token, keyword, mid))
        return parse_search_xml(SEARCH_4070)[0] if "4070" in keyword else []

    reg = registry(("nvidia-rtx-4070", "NVIDIA", "RTX 4070"), ("amd-rx-9070", "AMD", "RX 9070"))
    reg.loc[1, "is_active"] = "false"
    df, _ = scrape_newegg_prices(
        Resolver.from_files(),
        reg,
        get_config(),
        run_id="t",
        now=NOW,
        creds=CREDS,
        token_fn=lambda c: "tok",
        status_fn=lambda t, mid: status,
        search_fn=search,
        pause=0,
    )
    assert calls == [("tok", "GeForce RTX 4070", "44583")]  # inactive GPU not searched
    assert list(df.columns) == prices.PRICE_COLUMNS
    assert len(df) == 2 and set(df["retailer"]) == {"newegg"}


def test_request_errors_never_include_credentials(monkeypatch):
    monkeypatch.setattr(rakuten.time, "sleep", lambda s: None)

    def boom(*args, **kwargs):
        raise requests.ConnectionError(f"failed for {kwargs.get('data')} client-secret-XYZ")

    monkeypatch.setattr(rakuten.requests, "request", boom)
    with pytest.raises(RakutenError) as err:
        rakuten.fetch_token(CREDS)
    assert "client-secret-XYZ" not in str(err.value)
    assert str(err.value) == "ConnectionError during token request"


def test_rejected_credentials_message(monkeypatch):
    class Resp:
        status_code = 401
        text = "invalid_client client-secret-XYZ"

    monkeypatch.setattr(rakuten.requests, "request", lambda *a, **k: Resp())
    with pytest.raises(
        RakutenError, match=r"rejected the credentials for token request \(HTTP 401\)"
    ) as err:
        rakuten.fetch_token(CREDS)
    assert "client-secret-XYZ" not in str(err.value)


def test_redact_secrets_covers_rakuten(monkeypatch):
    monkeypatch.setenv("RAKUTEN_CLIENT_SECRET", "client-secret-XYZ")
    assert retailers.redact_secrets("oops client-secret-XYZ") == "oops ***"


def test_registry_and_skip_note_in_collection():
    assert "newegg" in retailers.ADAPTERS
    assert retailers.display_name("newegg") == "Newegg"

    def skip(*args, **kwargs):
        raise RetailerSkipped("Newegg partnership on Rakuten is 'pending', not approved yet")

    appended = []
    result = build.collect_retailer_prices(
        ["newegg"],
        None,
        pd.DataFrame(),
        get_config(),
        pd.DataFrame(columns=prices.PRICE_COLUMNS),
        run_id="t",
        now=NOW,
        adapters={"newegg": skip},
        append=appended.append,
    )
    assert result.notes == [
        "Newegg skipped: Newegg partnership on Rakuten is 'pending', not approved yet"
    ]
    assert result.fetch_failures == [] and appended == []


def test_config_enables_newegg():
    cfg = get_config()
    assert cfg.pricing.retailers == ["bestbuy", "newegg", "manual"]
    assert cfg.pricing.newegg_rakuten_mid == "44583"


@pytest.mark.parametrize("first_status", [429, 503, None])
def test_retry_preserves_authorization(monkeypatch, first_status):
    calls = []
    monkeypatch.setattr(rakuten.time, "sleep", lambda seconds: None)

    def request(*args, **kwargs):
        calls.append(dict(kwargs["headers"]))
        if len(calls) == 1 and first_status is None:
            raise requests.ConnectionError("temporary connection failure")
        response = requests.Response()
        response.status_code = first_status if len(calls) == 1 else 200
        return response

    monkeypatch.setattr(rakuten.requests, "request", request)
    response = rakuten._request(
        "GET",
        rakuten.SEARCH_URL,
        what="product search",
        headers={"Authorization": "Bearer test-token", "Accept": "application/xml"},
    )
    assert response.status_code == 200
    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert calls[1]["Authorization"] == "Bearer test-token"
    assert calls[1]["Accept"] == "application/xml"


@pytest.mark.parametrize(
    "title",
    [
        "Dell Tower Plus Desktop PC Intel Core Ultra 9 RTX 4070 32GB DDR5",
        "CLX Gaming Desktop GeForce RTX 4070 12GB 1TB NVMe SSD",
        "HAJAAN Gaming Desktop Tower PC GeForce RTX 4070 Windows 11",
        "ADAMANT Workstation Ryzen 9 9950X GeForce RTX 4070",
        "Mini PC GeForce RTX 4070 12GB",
        "95mm GPU Cooling Fan for GeForce RTX 4070",
        "VGA Graphics Card Cooler Replacement Fan GeForce RTX 4070",
        "RTX 4070 replacement cooling fans",
        "RTX 4070 thermal pad kit",
        "GeForce RTX 4070 water-block",
        "GeForce RTX 4070 capture card",
        "MINISFORUM eGPU Dock for RTX 4070 Graphics Card",
        "90 Degree Power Connector for RTX 4070 Graphics Card",
        "Three GPU coolers for RTX 4070 graphics cards",
        "RTX 4070 Artisan Keycap",
        "Full Cover Graphics Card Water Cooling Block for RTX 4070",
        "Monitors compatible with RTX 4070 graphics cards",
        "A cooler set for RTX 4070 graphics cards",
        "Blocking MOS for RTX 4070 graphics cards",
        "CyberPowerPC Gamer Master with RTX 4070",
        "ASUS ROG Zephyrus laptop with RTX 4070",
    ],
)
def test_systems_and_parts_never_become_prices_or_unresolved(title):
    item = parse_search_xml(SEARCH_4070)[0][0] | {"productname": title}
    obs, unresolved = items_to_observations(
        [item], "nvidia-rtx-4070", Resolver.from_files(), now=NOW, run_id="test"
    )
    assert obs == []
    assert unresolved == []


@pytest.mark.parametrize(
    "title",
    [
        "MSI Gaming GeForce RTX 4070 12GB Graphics Card Twin Fan",
        "ASUS Dual GeForce RTX 4070 12GB Desktop Graphics Card",
        "Gigabyte GeForce RTX 4070 12GB WINDFORCE Cooling System",
        "GeForce RTX 4070 12GB Water Cooled Graphics Card",
        "MSI GeForce RTX 4070 12GB VENTUS 3X OC",
        "ZOTAC Gaming GeForce RTX 4070 AMP Graphic Cards",
    ],
)
def test_standalone_cards_keep_cooling_and_desktop_descriptions(title):
    item = parse_search_xml(SEARCH_4070)[0][0] | {"productname": title}
    obs, unresolved = items_to_observations(
        [item], "nvidia-rtx-4070", Resolver.from_files(), now=NOW, run_id="test"
    )
    assert len(obs) == 1
    assert obs[0]["title_raw"] == title
    assert unresolved == []


@pytest.mark.parametrize(
    "title",
    [
        "Two FY09015M12LPA fans per set, suitable for GeForce RTX 4070 12GB graphics cards",
        "Bitspower Titan GPU Cooling Expansion Kit for MSI GeForce RTX 4070",
        "Phanteks Glacier ASUS GPU Block for RTX 4070 Full Cover copper block",
    ],
)
def test_live_accessory_titles_are_excluded(title):
    item = parse_search_xml(SEARCH_4070)[0][0] | {"productname": title}
    obs, unresolved = items_to_observations(
        [item], "nvidia-rtx-4070", Resolver.from_files(), now=NOW, run_id="test"
    )
    assert obs == [] and unresolved == []


def test_model_only_product_is_held_for_review():
    item = parse_search_xml(SEARCH_4070)[0][0] | {
        "productname": "BITSPOWER NEBULA CLASSIC GeForce RTX 5090 VENTUS"
    }
    obs, unresolved = items_to_observations(
        [item], "nvidia-rtx-5090", Resolver.from_files(), now=NOW, run_id="test"
    )
    assert obs == [] and len(unresolved) == 1


def test_unknown_model_suffix_cannot_fuzzy_match_plain_card():
    item = parse_search_xml(SEARCH_4070)[0][0] | {
        "productname": "SAPPHIRE PULSE Radeon RX 9070 GRE Graphics Card"
    }
    obs, _ = items_to_observations(
        [item], "amd-rx-9070", Resolver.from_files(), now=NOW, run_id="test"
    )
    assert obs == []


@pytest.mark.parametrize("memory,expected", [("6GB", 0), ("GV-N3050WF2-6GD", 0), ("8GB", 1)])
def test_memory_must_match_benchmarked_variant(memory, expected):
    item = parse_search_xml(SEARCH_4070)[0][0] | {
        "productname": f"GIGABYTE GeForce RTX 3050 Graphics Card {memory}"
    }
    obs, _ = items_to_observations(
        [item],
        "nvidia-rtx-3050",
        Resolver.from_files(),
        now=NOW,
        run_id="test",
        expected_vram=8,
    )
    assert len(obs) == expected


def test_catalog_marks_unavailable_offer_invalid_but_keeps_it_for_history():
    from svi.scrapers.rakuten import catalog_items_to_observations

    item = parse_search_xml(SEARCH_4070)[0][0] | {"availability": "out-of-stock"}
    rows, unresolved = catalog_items_to_observations(
        [item],
        Resolver.from_files(),
        registry(("nvidia-rtx-4070", "NVIDIA", "RTX 4070")),
        now=NOW,
        run_id="catalog",
    )
    assert len(rows) == 1
    assert not rows.iloc[0]["in_stock"]
    checked = prices.validate_observations(
        rows, pd.DataFrame(columns=prices.PRICE_COLUMNS), get_config().pricing, now=NOW
    )
    assert not checked.iloc[0]["is_valid"]
    assert checked.iloc[0]["invalid_reason"] == "not_in_stock"
    assert unresolved == []
