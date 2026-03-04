"""Tests for JSON script detection and extraction."""
import pytest
from bs4 import BeautifulSoup

from llm_html.cleaner.scripts import (
    is_json_script,
    extract_json_from_script,
    extract_ssr_data,
    extract_structured_data_from_soup,
    extract_all_data,
    ExtractedData,
)


class TestIsJsonScript:
    """Tests for is_json_script function."""

    def test_detects_json_ld(self):
        """Detect JSON-LD script by type."""
        html = '<script type="application/ld+json">{"@context":"https://schema.org"}</script>'
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        assert is_json_script(script) is True

    def test_detects_application_json(self):
        """Detect application/json script by type."""
        html = '<script type="application/json">{"data":"value"}</script>'
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        assert is_json_script(script) is True

    def test_detects_next_data(self):
        """Detect Next.js __NEXT_DATA__ script by ID."""
        html = '<script id="__NEXT_DATA__">{"props":{}}</script>'
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        assert is_json_script(script) is True

    def test_detects_nuxt_data(self):
        """Detect Nuxt.js __NUXT__ script by ID."""
        html = '<script id="__NUXT__">{"data":[]}</script>'
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        assert is_json_script(script) is True

    def test_detects_json_content(self):
        """Detect JSON by parsing content."""
        html = '<script>{"valid":"json"}</script>'
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        assert is_json_script(script) is True

    def test_rejects_regular_script(self):
        """Reject regular JavaScript."""
        html = '<script>console.log("hello");</script>'
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        assert is_json_script(script) is False

    def test_rejects_empty_script(self):
        """Reject empty script."""
        html = "<script></script>"
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        assert is_json_script(script) is False


class TestExtractJsonFromScript:
    """Tests for extract_json_from_script function."""

    def test_extracts_object(self):
        """Extract JSON object from script."""
        html = '<script type="application/json">{"key":"value"}</script>'
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        data = extract_json_from_script(script)

        assert data is not None
        assert data["key"] == "value"

    def test_extracts_array(self):
        """Extract JSON array from script."""
        html = '<script type="application/json">[1,2,3]</script>'
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        data = extract_json_from_script(script)

        assert data is not None
        assert data == [1, 2, 3]

    def test_returns_none_for_invalid(self):
        """Return None for invalid JSON."""
        html = "<script>not json</script>"
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        data = extract_json_from_script(script)

        assert data is None

    def test_returns_none_for_empty(self):
        """Return None for empty script."""
        html = "<script></script>"
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script")
        data = extract_json_from_script(script)

        assert data is None


class TestExtractSSRData:
    """Tests for extract_ssr_data function."""

    def test_extracts_next_data(self):
        """Extract Next.js SSR data."""
        # Pattern matches __NEXT_DATA__ = {...} format
        html = '<script>window.__NEXT_DATA__={"props":{"pageProps":{"data":"value"}}}</script>'
        data = extract_ssr_data(html)

        assert "next" in data
        assert data["next"]["props"]["pageProps"]["data"] == "value"

    def test_extracts_nuxt_data(self):
        """Extract Nuxt.js SSR data."""
        html = '''<script>window.__NUXT__={"data":[{"items":[1,2,3]}]}</script>'''
        data = extract_ssr_data(html)

        assert "nuxt" in data
        assert data["nuxt"]["data"][0]["items"] == [1, 2, 3]

    def test_handles_missing_data(self):
        """Handle HTML without SSR data."""
        html = "<html><body>No SSR</body></html>"
        data = extract_ssr_data(html)

        assert data == {}


class TestExtractStructuredData:
    """Tests for extract_structured_data_from_soup function."""

    def test_extracts_json_ld(self):
        """Extract JSON-LD structured data."""
        html = '''<html><body>
        <script type="application/ld+json">
        {"@context":"https://schema.org","@type":"Product","name":"Test"}
        </script>
        </body></html>'''
        soup = BeautifulSoup(html, "lxml")
        data = extract_structured_data_from_soup(soup)

        assert len(data) == 1
        assert data[0]["@type"] == "Product"
        assert data[0]["name"] == "Test"

    def test_extracts_multiple_json_ld(self):
        """Extract multiple JSON-LD blocks."""
        html = '''<html><body>
        <script type="application/ld+json">{"@type":"Organization"}</script>
        <script type="application/ld+json">{"@type":"WebPage"}</script>
        </body></html>'''
        soup = BeautifulSoup(html, "lxml")
        data = extract_structured_data_from_soup(soup)

        assert len(data) == 2
        types = [d["@type"] for d in data]
        assert "Organization" in types
        assert "WebPage" in types

    def test_handles_json_ld_array(self):
        """Handle JSON-LD containing array."""
        html = '''<html><body>
        <script type="application/ld+json">
        [{"@type":"Product"},{"@type":"Review"}]
        </script>
        </body></html>'''
        soup = BeautifulSoup(html, "lxml")
        data = extract_structured_data_from_soup(soup)

        assert len(data) == 2


class TestExtractAllData:
    """Tests for extract_all_data function."""

    def test_extracts_all_types(self):
        """Extract all types of data."""
        html = '''<html><body>
        <script type="application/ld+json">{"@type":"Product","name":"Test"}</script>
        </body></html>'''
        soup = BeautifulSoup(html, "lxml")
        data = extract_all_data(soup, html)

        assert isinstance(data, ExtractedData)
        assert len(data.structured_data) == 1
        assert data.structured_data[0]["@type"] == "Product"

    def test_combined_extraction(self):
        """Test combined SSR and structured data extraction."""
        html = '''<html><body>
        <script>window.__NEXT_DATA__={"props":{}}</script>
        <script type="application/ld+json">{"@context":"https://schema.org"}</script>
        </body></html>'''
        soup = BeautifulSoup(html, "lxml")
        data = extract_all_data(soup, html)

        assert len(data.structured_data) == 1
        assert "next" in data.ssr_data
