"""Tests for SSR hydration extraction."""
import pytest
import json

from llm_html.cleaner.extractors.hydration import (
    HydrationExtractor,
    HydrationData,
    Framework,
    extract_hydration,
    detect_framework,
)


class TestFrameworkDetection:
    """Tests for SSR framework detection."""

    def test_detect_nextjs_pages(self):
        """Detect Next.js Pages Router."""
        html = '<script id="__NEXT_DATA__" type="application/json">{}</script>'
        assert detect_framework(html) == Framework.NEXTJS_PAGES

    def test_detect_nextjs_app(self):
        """Detect Next.js App Router."""
        html = '<script>self.__next_f.push([1, "data"])</script>'
        assert detect_framework(html) == Framework.NEXTJS_APP

    def test_detect_nuxt2(self):
        """Detect Nuxt 2."""
        html = '<script>window.__NUXT__={"data":[]}</script>'
        assert detect_framework(html) == Framework.NUXT2

    def test_detect_nuxt3(self):
        """Detect Nuxt 3."""
        html = '<script type="application/json" id="__NUXT_DATA__">[]</script>'
        assert detect_framework(html) == Framework.NUXT3

    def test_detect_sveltekit(self):
        """Detect SvelteKit."""
        html = '<script>__sveltekit_abc123={"data":{}}</script>'
        assert detect_framework(html) == Framework.SVELTEKIT

    def test_detect_remix(self):
        """Detect Remix."""
        html = '<script>window.__remixContext={"state":{}}</script>'
        assert detect_framework(html) == Framework.REMIX

    def test_detect_gatsby(self):
        """Detect Gatsby."""
        html = '<script>window.___gatsby={"data":{}}</script>'
        assert detect_framework(html) == Framework.GATSBY

    def test_detect_qwik(self):
        """Detect Qwik."""
        html = '<script type="qwik/json">{}</script>'
        assert detect_framework(html) == Framework.QWIK

    def test_detect_unknown(self):
        """Return UNKNOWN for regular HTML."""
        html = '<html><body><h1>Hello</h1></body></html>'
        assert detect_framework(html) == Framework.UNKNOWN


class TestNextJSPagesExtraction:
    """Tests for Next.js Pages Router extraction."""

    def test_extract_basic(self):
        """Extract basic __NEXT_DATA__."""
        data = {
            "props": {
                "pageProps": {
                    "products": [{"id": 1, "name": "Test"}]
                }
            },
            "page": "/products",
            "buildId": "abc123"
        }
        html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'

        result = extract_hydration(html)

        assert result.success
        assert result.framework == Framework.NEXTJS_PAGES
        assert result.build_id == "abc123"
        assert result.page_path == "/products"
        assert result.page_props["products"][0]["name"] == "Test"

    def test_extract_with_locale(self):
        """Extract with locale information."""
        data = {
            "props": {"pageProps": {}},
            "locale": "ko",
            "page": "/cars"
        }
        html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'

        result = extract_hydration(html)

        assert result.success
        assert result.locale == "ko"

    def test_extract_empty_pageprops(self):
        """Handle empty pageProps."""
        data = {"props": {}, "page": "/"}
        html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'

        result = extract_hydration(html)

        assert result.success
        assert result.page_props == {}

    def test_extract_not_found(self):
        """Return error when __NEXT_DATA__ not found."""
        html = '<html><body>No Next.js here</body></html>'

        extractor = HydrationExtractor()
        result = extractor.extract(html, Framework.NEXTJS_PAGES)

        assert not result.success
        assert "not found" in result.error


class TestNextJSAppExtraction:
    """Tests for Next.js App Router extraction."""

    def test_extract_streaming_chunks(self):
        """Extract and aggregate streaming chunks."""
        html = '''
        <script>self.__next_f.push([1, "{\\"data\\":\\"chunk1\\"}"])</script>
        <script>self.__next_f.push([1, "{\\"more\\":\\"chunk2\\"}"])</script>
        '''

        result = extract_hydration(html)

        assert result.success
        assert result.framework == Framework.NEXTJS_APP
        assert result.extraction_method == "streaming"

    def test_extract_no_chunks(self):
        """Handle missing streaming data."""
        html = '<html><body>No streaming</body></html>'

        extractor = HydrationExtractor()
        result = extractor.extract(html, Framework.NEXTJS_APP)

        assert not result.success


class TestNuxtExtraction:
    """Tests for Nuxt extraction."""

    def test_extract_nuxt2(self):
        """Extract Nuxt 2 data."""
        data = {
            "data": [{"items": [1, 2, 3]}],
            "state": {"user": None}
        }
        html = f'<script>window.__NUXT__={json.dumps(data)}</script>'

        result = extract_hydration(html)

        assert result.success
        assert result.framework == Framework.NUXT2
        assert result.page_props["items"] == [1, 2, 3]

    def test_extract_nuxt3(self):
        """Extract Nuxt 3 data."""
        data = {"products": [{"id": 1}], "meta": {"total": 100}}
        html = f'<script type="application/json" id="__NUXT_DATA__">{json.dumps(data)}</script>'

        result = extract_hydration(html)

        assert result.success
        assert result.framework == Framework.NUXT3
        assert result.page_props["products"][0]["id"] == 1


class TestSvelteKitExtraction:
    """Tests for SvelteKit extraction."""

    def test_extract_sveltekit(self):
        """Extract SvelteKit data."""
        data = {"data": {"posts": [{"title": "Hello"}]}}
        html = f'<script>__sveltekit_data123={json.dumps(data)}</script>'

        result = extract_hydration(html)

        assert result.success
        assert result.framework == Framework.SVELTEKIT
        assert result.page_props["posts"][0]["title"] == "Hello"


class TestRemixExtraction:
    """Tests for Remix extraction."""

    def test_extract_remix(self):
        """Extract Remix loaderData."""
        data = {
            "state": {
                "loaderData": {
                    "root": {"user": {"name": "Test"}}
                }
            }
        }
        html = f'<script>window.__remixContext={json.dumps(data)}</script>'

        result = extract_hydration(html)

        assert result.success
        assert result.framework == Framework.REMIX
        assert "root" in result.page_props


class TestGatsbyExtraction:
    """Tests for Gatsby extraction."""

    def test_extract_gatsby(self):
        """Extract Gatsby data."""
        data = {"pagePath": "/about", "data": {"site": {"title": "My Site"}}}
        html = f'<script>window.___gatsby={json.dumps(data)}</script>'

        result = extract_hydration(html)

        assert result.success
        assert result.framework == Framework.GATSBY


class TestQwikExtraction:
    """Tests for Qwik extraction."""

    def test_extract_qwik(self):
        """Extract Qwik data."""
        data = {"ctx": {"qwik": True}, "objs": [1, 2, 3]}
        html = f'<script type="qwik/json">{json.dumps(data)}</script>'

        result = extract_hydration(html)

        assert result.success
        assert result.framework == Framework.QWIK


class TestHydrationExtractor:
    """Tests for HydrationExtractor class."""

    def test_auto_detect_and_extract(self):
        """Auto-detect framework and extract."""
        data = {"props": {"pageProps": {"test": True}}, "page": "/"}
        html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'

        extractor = HydrationExtractor()
        result = extractor.extract(html)  # No framework hint

        assert result.success
        assert result.framework == Framework.NEXTJS_PAGES

    def test_extract_all(self):
        """Extract from multiple sources."""
        # HTML with both Next.js and JSON-LD
        html = '''
        <script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{}}}</script>
        '''

        extractor = HydrationExtractor()
        results = extractor.extract_all(html)

        assert len(results) >= 1
        assert any(r.framework == Framework.NEXTJS_PAGES for r in results)

    def test_empty_html(self):
        """Handle empty HTML."""
        result = extract_hydration("")

        assert not result.success
        assert "Empty" in result.error

    def test_invalid_json(self):
        """Handle invalid JSON in script tag."""
        html = '<script id="__NEXT_DATA__" type="application/json">{invalid json}</script>'

        result = extract_hydration(html)

        assert not result.success
        assert "parse error" in result.error.lower()


class TestHydrationData:
    """Tests for HydrationData dataclass."""

    def test_has_data_true(self):
        """has_data returns True when data present."""
        data = HydrationData(
            framework=Framework.NEXTJS_PAGES,
            page_props={"test": True},
            success=True
        )
        assert data.has_data

    def test_has_data_false_empty(self):
        """has_data returns False when page_props empty."""
        data = HydrationData(
            framework=Framework.NEXTJS_PAGES,
            page_props={},
            success=True
        )
        assert not data.has_data

    def test_has_data_false_not_success(self):
        """has_data returns False when not successful."""
        data = HydrationData(
            framework=Framework.NEXTJS_PAGES,
            page_props={"test": True},
            success=False
        )
        assert not data.has_data


class TestRealWorldExamples:
    """Tests with real-world-like HTML examples."""

    def test_nextjs_ecommerce_page(self):
        """Extract from e-commerce product page."""
        data = {
            "props": {
                "pageProps": {
                    "product": {
                        "id": "12345",
                        "name": "Test Product",
                        "price": 99.99,
                        "currency": "USD",
                        "images": ["img1.jpg", "img2.jpg"],
                        "variants": [
                            {"size": "S", "stock": 10},
                            {"size": "M", "stock": 5}
                        ]
                    }
                }
            },
            "page": "/products/[id]",
            "buildId": "prod-build-123"
        }
        html = f'''
        <!DOCTYPE html>
        <html>
        <head><title>Product</title></head>
        <body>
            <div id="__next">Loading...</div>
            <script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>
        </body>
        </html>
        '''

        result = extract_hydration(html)

        assert result.success
        assert result.page_props["product"]["price"] == 99.99
        assert len(result.page_props["product"]["variants"]) == 2

    def test_nuxt_listing_page(self):
        """Extract from Nuxt listing page."""
        data = {
            "data": [{
                "cars": [
                    {"id": 1, "brand": "Toyota", "price": 25000},
                    {"id": 2, "brand": "Honda", "price": 22000}
                ],
                "pagination": {"page": 1, "total": 100}
            }]
        }
        html = f'''
        <html>
        <body>
            <div id="__nuxt"></div>
            <script>window.__NUXT__={json.dumps(data)}</script>
        </body>
        </html>
        '''

        result = extract_hydration(html)

        assert result.success
        assert result.framework == Framework.NUXT2
        assert result.page_props["cars"][0]["brand"] == "Toyota"
