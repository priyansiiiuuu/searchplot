import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from collections import Counter
import re
import socket
import ipaddress


USER_AGENT = "SearchPilotBot/1.0"
REQUEST_TIMEOUT = 15
MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB maximum response size limit

def is_safe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_loopback or
            ip.is_private or
            ip.is_link_local or
            ip.is_multicast or
            ip.is_reserved or
            ip.is_unspecified
        ):
            return False
        # Explicitly check cloud metadata
        if ip_str in ("169.254.169.254", "fe80::254"):
            return False
        return True
    except ValueError:
        return False

def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        # Resolve hostname to IPs (both IPv4 and IPv6)
        addr_info = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if not is_safe_ip(ip_str):
                return False
        return True
    except Exception:
        return False

def safe_requests_get(url: str, **kwargs):
    if not is_safe_url(url):
        raise requests.exceptions.RequestException(
            f"Access to URL {url} is blocked for security reasons (SSRF Protection)."
        )
    
    allow_redirects = kwargs.pop("allow_redirects", True)
    max_redirects = 5
    current_url = url
    redirect_count = 0
    
    while True:
        response = requests.get(current_url, allow_redirects=False, stream=True, **kwargs)
        
        # Check Content-Length if present
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > MAX_RESPONSE_SIZE:
                    raise requests.exceptions.RequestException("Response size limit exceeded.")
            except ValueError:
                pass
        
        # Read chunks to limit size
        content = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            content.extend(chunk)
            if len(content) > MAX_RESPONSE_SIZE:
                raise requests.exceptions.RequestException("Response size limit exceeded.")
        
        response._content = bytes(content)
        
        # Follow redirects manually checking resolved IPs at each hop
        if response.status_code in (301, 302, 303, 307, 308):
            if not allow_redirects:
                return response
            
            redirect_count += 1
            if redirect_count > max_redirects:
                raise requests.exceptions.TooManyRedirects("Too many redirects.")
            
            location = response.headers.get("location")
            if not location:
                return response
            
            current_url = urljoin(current_url, location)
            current_url = normalize_url(current_url)
            
            if not is_safe_url(current_url):
                raise requests.exceptions.RequestException(
                    f"Access to redirect URL {current_url} is blocked for security reasons."
                )
        else:
            return response


BLOCKED_PATH_PATTERNS = (
    "/special:",
    "/talk:",
    "/user:",
    "/file:",
    "/help:",
    "/wikipedia:",
    "/template:",
    "/category:",
    "/portal:",
    "/module:",
    "/mediawiki:",
)

BLOCKED_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".pdf", ".zip", ".rar", ".7z",
    ".mp4", ".mp3", ".wav", ".avi", ".mov",
    ".css", ".js", ".xml", ".json",
    ".woff", ".woff2", ".ttf", ".ico",
)


# =========================================================
# URL HELPERS
# =========================================================

def normalize_url(url: str) -> str:
    url, _ = urldefrag(url)

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    path = parsed.path or "/"

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return f"{scheme}://{netloc}{path}"


def get_hostname(url: str) -> str:
    return urlparse(url).netloc.lower().split(":")[0]


def is_blocked_path(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()

    for pattern in BLOCKED_PATH_PATTERNS:
        if pattern in path:
            return True

    for extension in BLOCKED_EXTENSIONS:
        if path.endswith(extension):
            return True

    return False


def is_crawlable_url(url: str, target_hostname: str) -> bool:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.netloc.lower().split(":")[0]

    if hostname != target_hostname:
        return False

    if is_blocked_path(url):
        return False

    return True


# =========================================================
# PAGE TITLE
# =========================================================

def get_page_title(soup):
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    return ""


# =========================================================
# SITEMAP DISCOVERY
# =========================================================

def discover_sitemaps(start_url: str):
    """
    Find sitemap URLs from robots.txt and common sitemap locations.
    """

    parsed = urlparse(start_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    sitemap_candidates = []

    # -----------------------------------------------------
    # 1. robots.txt
    # -----------------------------------------------------

    robots_url = urljoin(base_url, "/robots.txt")

    try:
        response = safe_requests_get(
            robots_url,
            timeout=10,
            headers={"User-Agent": USER_AGENT}
        )

        if response.status_code == 200:

            for line in response.text.splitlines():

                line = line.strip()

                if line.lower().startswith("sitemap:"):

                    sitemap_url = line.split(
                        ":",
                        1
                    )[1].strip()

                    if sitemap_url:
                        sitemap_candidates.append(
                            sitemap_url
                        )

            print(
                f"[SearchPilot] robots.txt sitemap candidates: "
                f"{len(sitemap_candidates)}"
            )

    except requests.RequestException as error:

        print(
            f"[SearchPilot] robots.txt failed: {error}"
        )

    # -----------------------------------------------------
    # 2. Common sitemap locations
    # -----------------------------------------------------

    common_sitemaps = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/wp-sitemap.xml",
    ]

    for path in common_sitemaps:

        sitemap_url = urljoin(
            base_url,
            path
        )

        if sitemap_url not in sitemap_candidates:
            sitemap_candidates.append(
                sitemap_url
            )

    return list(
        dict.fromkeys(sitemap_candidates)
    )


def extract_sitemap_urls(
    sitemap_url: str,
    target_hostname: str,
    visited_sitemaps=None
):
    """
    Extract URLs from a sitemap or sitemap index.
    """

    if visited_sitemaps is None:
        visited_sitemaps = set()

    sitemap_url = normalize_url(
        sitemap_url
    )

    if sitemap_url in visited_sitemaps:
        return []

    visited_sitemaps.add(
        sitemap_url
    )

    urls = []

    try:

        response = safe_requests_get(
            sitemap_url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": USER_AGENT
            }
        )

        if response.status_code != 200:

            print(
                f"[SearchPilot] Sitemap unavailable "
                f"({response.status_code}): "
                f"{sitemap_url}"
            )

            return []

        content = response.text

        # -------------------------------------------------
        # Parse XML
        # -------------------------------------------------

        soup = BeautifulSoup(
            content,
            "xml"
        )

        # -------------------------------------------------
        # Sitemap INDEX
        # -------------------------------------------------

        child_sitemaps = soup.find_all(
            "sitemap"
        )

        if child_sitemaps:

            print(
                f"[SearchPilot] Sitemap index found: "
                f"{sitemap_url}"
            )

            for sitemap in child_sitemaps:

                loc = sitemap.find("loc")

                if not loc:
                    continue

                child_url = loc.get_text(
                    strip=True
                )

                if not child_url:
                    continue

                # Enforce same-host restriction for child sitemaps before fetching them
                if get_hostname(child_url) != target_hostname:
                    print(f"[SearchPilot] Skipped external child sitemap: {child_url} (hostname mismatch)")
                    continue

                urls.extend(
                    extract_sitemap_urls(
                        child_url,
                        target_hostname,
                        visited_sitemaps
                    )
                )

            return list(
                dict.fromkeys(urls)
            )

        # -------------------------------------------------
        # NORMAL URLSET
        # -------------------------------------------------

        loc_tags = soup.find_all(
            "loc"
        )

        for loc in loc_tags:

            page_url = loc.get_text(
                strip=True
            )

            if not page_url:
                continue

            page_url = normalize_url(
                page_url
            )

            if is_crawlable_url(
                page_url,
                target_hostname
            ):

                urls.append(
                    page_url
                )

        print(
            f"[SearchPilot] Extracted "
            f"{len(urls)} URLs from "
            f"{sitemap_url}"
        )

    except requests.RequestException as error:

        print(
            f"[SearchPilot] Sitemap request failed: "
            f"{sitemap_url} -> {error}"
        )

    except Exception as error:

        print(
            f"[SearchPilot] Sitemap parsing failed: "
            f"{sitemap_url} -> {error}"
        )

    return list(
        dict.fromkeys(urls)
    )


# =========================================================
# SINGLE PAGE CRAWLER
# =========================================================

def crawl_page(url: str):

    url = normalize_url(url)

    response = safe_requests_get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": USER_AGENT
        },
        allow_redirects=True
    )

    response.raise_for_status()

    final_url = normalize_url(
        response.url
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # =====================================================
    # BASIC PAGE INFORMATION
    # =====================================================

    title = get_page_title(soup)

    description_tag = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    description = (
        description_tag.get(
            "content",
            ""
        ).strip()
        if description_tag
        else ""
    )

    # =====================================================
    # VIEWPORT
    # =====================================================

    viewport_tag = soup.find(
        "meta",
        attrs={"name": "viewport"}
    )

    viewport = (
        viewport_tag.get(
            "content",
            ""
        ).strip()
        if viewport_tag
        else None
    )

    # =====================================================
    # HEADINGS
    # =====================================================

    headings = {
        "h1": [
            h.get_text(" ", strip=True)
            for h in soup.find_all("h1")
        ],
        "h2": [
            h.get_text(" ", strip=True)
            for h in soup.find_all("h2")
        ],
        "h3": [
            h.get_text(" ", strip=True)
            for h in soup.find_all("h3")
        ],
    }

    # =====================================================
    # IMAGES
    # =====================================================

    images = soup.find_all("img")

    images_missing_alt = [
        img.get("src", "")
        for img in images
        if not img.get("alt", "").strip()
    ]

    # =====================================================
    # STRUCTURED DATA
    # =====================================================

    structured_data = soup.find_all(
        "script",
        attrs={
            "type": "application/ld+json"
        }
    )

    structured_data_count = len(
        structured_data
    )

    # =====================================================
    # LINKS
    # =====================================================

    target_hostname = get_hostname(
        final_url
    )

    internal_links = []
    external_links = []

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href",
            ""
        ).strip()

        if not href:
            continue

        if href.startswith(
            (
                "javascript:",
                "mailto:",
                "tel:",
                "#"
            )
        ):
            continue

        absolute_url = urljoin(
            final_url,
            href
        )

        absolute_url = normalize_url(
            absolute_url
        )

        link_hostname = get_hostname(absolute_url)

        if link_hostname == target_hostname:
            if is_crawlable_url(
                absolute_url,
                target_hostname
            ):
                internal_links.append(
                    absolute_url
                )
        else:
            parsed_link = urlparse(
                absolute_url
            )

            if parsed_link.scheme in (
                "http",
                "https"
            ):

                external_links.append(
                    absolute_url
                )

    internal_links = list(
        dict.fromkeys(
            internal_links
        )
    )

    external_links = list(
        dict.fromkeys(
            external_links
        )
    )

    # =====================================================
    # REMOVE NON-CONTENT
    # =====================================================

    for element in soup([
        "script",
        "style",
        "noscript",
        "nav",
        "footer",
        "header"
    ]):

        element.decompose()

    page_text = soup.get_text(
        " ",
        strip=True
    )

    word_count = len(
        page_text.split()
    )

    # =====================================================
    # KEYWORD ANALYSIS
    # =====================================================

    stop_words = {
        "the", "and", "for", "that",
        "this", "with", "from",
        "you", "your", "are", "was",
        "were", "have", "has", "had",
        "not", "but", "they",
        "their", "there", "what",
        "when", "where", "which",
        "who", "how", "why", "will",
        "would", "could", "should",
        "can", "about", "into",
        "than", "then", "them",
        "these", "those", "our",
        "out", "all", "more",
        "some", "any", "one",
        "two", "also", "only",
        "other", "its", "it's",
        "been", "being", "over",
        "under", "after", "before",
        "between", "through",
        "during", "such", "very",
        "www", "http", "https",
        "com", "free", "home",
        "page", "menu", "search",
        "login", "sign", "read",
        "edit", "view", "main",
        "content", "article",
        "articles"
    }

    words = re.findall(
        r"\b[a-zA-Z][a-zA-Z0-9'-]{2,}\b",
        page_text.lower()
    )

    filtered_words = [
        word
        for word in words
        if word not in stop_words
    ]

    word_counts = Counter(
        filtered_words
    )

    bigrams = [
        f"{filtered_words[i]} "
        f"{filtered_words[i + 1]}"
        for i in range(
            len(filtered_words) - 1
        )
    ]

    bigram_counts = Counter(
        bigrams
    )

    trigrams = [
        f"{filtered_words[i]} "
        f"{filtered_words[i + 1]} "
        f"{filtered_words[i + 2]}"
        for i in range(
            len(filtered_words) - 2
        )
    ]

    trigram_counts = Counter(
        trigrams
    )

    keywords = []

    for word, count in word_counts.most_common(10):

        if count >= 2:

            keywords.append({
                "keyword": word,
                "count": count,
                "density": round(
                    (count / word_count) * 100,
                    2
                ) if word_count else 0,
                "type": "keyword"
            })

    for phrase, count in bigram_counts.most_common(10):

        if count >= 2:

            keywords.append({
                "keyword": phrase,
                "count": count,
                "density": round(
                    (count / word_count) * 100,
                    2
                ) if word_count else 0,
                "type": "phrase"
            })

    for phrase, count in trigram_counts.most_common(10):

        if count >= 2:

            keywords.append({
                "keyword": phrase,
                "count": count,
                "density": round(
                    (count / word_count) * 100,
                    2
                ) if word_count else 0,
                "type": "phrase"
            })

    keywords.sort(
        key=lambda x: x["count"],
        reverse=True
    )

    top_keywords = keywords[:20]

    # =====================================================
    # CANONICAL
    # =====================================================

    canonical_tag = soup.find(
        "link",
        attrs={"rel": "canonical"}
    )

    canonical = (
        urljoin(
            final_url,
            canonical_tag.get("href")
        )
        if canonical_tag
        and canonical_tag.get("href")
        else None
    )

    if canonical:
        canonical = normalize_url(
            canonical
        )

    # =====================================================
    # ROBOTS META
    # =====================================================

    robots_tag = soup.find(
        "meta",
        attrs={"name": "robots"}
    )

    robots = (
        robots_tag.get(
            "content",
            ""
        ).strip()
        if robots_tag
        else None
    )

    # =====================================================
    # OPEN GRAPH
    # =====================================================

    og_tags = {}

    for tag in soup.find_all("meta"):

        property_name = tag.get(
            "property"
        )

        if (
            property_name
            and property_name.startswith("og:")
        ):

            og_tags[property_name] = tag.get(
                "content",
                ""
            )

    # =====================================================
    # ROBOTS.TXT
    # =====================================================

    robots_url = urljoin(
        final_url,
        "/robots.txt"
    )

    try:

        robots_response = safe_requests_get(
            robots_url,
            timeout=10,
            headers={
                "User-Agent": USER_AGENT
            }
        )

        robots_txt_exists = (
            robots_response.status_code == 200
        )

    except requests.RequestException:

        robots_txt_exists = False

    # =====================================================
    # SITEMAP
    # =====================================================

    sitemap_url = urljoin(
        final_url,
        "/sitemap.xml"
    )

    try:

        sitemap_response = safe_requests_get(
            sitemap_url,
            timeout=10,
            headers={
                "User-Agent": USER_AGENT
            }
        )

        sitemap_exists = (
            sitemap_response.status_code == 200
        )

    except requests.RequestException:

        sitemap_exists = False

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    return {

        "url": final_url,

        "status_code": response.status_code,

        "seo": {

            "title": {
                "value": title,
                "length": len(title)
            },

            "meta_description": {
                "value": description,
                "length": len(description)
            },

            "h1": {
                "count": len(headings["h1"]),
                "values": headings["h1"]
            },

            "images": {
                "total": len(images),
                "missing_alt": len(images_missing_alt),
                "missing_alt_sources": images_missing_alt
            },

            "canonical": canonical,

            "robots": robots,

            "robots_txt": {
                "url": robots_url,
                "exists": robots_txt_exists
            },

            "sitemap": {
                "url": sitemap_url,
                "exists": sitemap_exists
            },

            "viewport": viewport,

            "open_graph": og_tags,

            "structured_data": {
                "count": structured_data_count,
                "exists": structured_data_count > 0
            }
        },

        "content": {

            "word_count": word_count,

            "headings": headings,

            "keywords": top_keywords,

            "text": page_text
        },

        "links": {

            "internal": len(internal_links),

            "external": len(external_links),

            "internal_urls": internal_links,

            "external_urls": external_links
        }
    }


# =========================================================
# FULL SITE CRAWLER
# =========================================================

def crawl_site(
    start_url: str,
    max_pages: int = 20
):

    start_url = normalize_url(
        start_url
    )

    target_hostname = get_hostname(
        start_url
    )

    # =====================================================
    # PARSE ROBOTS.TXT
    # =====================================================
    from urllib.robotparser import RobotFileParser
    rp = RobotFileParser()
    has_robots = False
    
    parsed = urlparse(start_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urljoin(base_url, "/robots.txt")

    try:
        response = safe_requests_get(
            robots_url,
            timeout=10,
            headers={"User-Agent": USER_AGENT}
        )
        if response.status_code == 200:
            rp.parse(response.text.splitlines())
            has_robots = True
            print(f"[SearchPilot] Successfully parsed robots.txt rules for {target_hostname}")
    except Exception as e:
        print(f"[SearchPilot] Malformed or unavailable robots.txt for {target_hostname}: {e}")

    # =====================================================
    # DISCOVER SITEMAP URLs
    # =====================================================

    sitemap_files = discover_sitemaps(
        start_url
    )

    sitemap_urls = []

    for sitemap_file in sitemap_files:

        discovered = extract_sitemap_urls(
            sitemap_file,
            target_hostname
        )

        sitemap_urls.extend(
            discovered
        )

    sitemap_urls = list(
        dict.fromkeys(
            sitemap_urls
        )
    )

    print(
        f"[SearchPilot] Sitemap discovered "
        f"{len(sitemap_urls)} URLs."
    )

    # =====================================================
    # BUILD QUEUE
    # =====================================================

    queue = []
    queued = set()

    # Sitemap URLs get priority.
    # This is important.
    for page_url in sitemap_urls:

        if len(queue) >= max_pages:
            break

        if not is_crawlable_url(
            page_url,
            target_hostname
        ):
            continue

        if has_robots and not rp.can_fetch("SearchPilotBot", page_url):
            if page_url != start_url:
                continue

        page_url = normalize_url(
            page_url
        )

        if page_url not in queued:

            queued.add(
                page_url
            )

            queue.append(
                page_url
            )

    # Start URL always gets priority too.
    if (
        start_url not in queued
        and len(queue) < max_pages
    ):

        queue.insert(
            0,
            start_url
        )

        queued.add(
            start_url
        )

    visited = set()
    crawled_urls = set()
    results = []

    # =====================================================
    # CRAWL
    # =====================================================

    while queue and len(crawled_urls) < max_pages:

        current_url = queue.pop(0)

        current_url = normalize_url(
            current_url
        )

        if current_url in visited:
            continue

        if current_url in crawled_urls:
            continue

        if not is_crawlable_url(
            current_url,
            target_hostname
        ):
            continue

        # Check robots.txt disallow rules (except for the initial start_url homepage)
        if has_robots and current_url != start_url and not rp.can_fetch("SearchPilotBot", current_url):
            print(f"[SearchPilot] Skipped disallowed page: {current_url}")
            continue

        visited.add(
            current_url
        )

        print(
            f"[SearchPilot] Crawling "
            f"{len(crawled_urls) + 1}/{max_pages}: "
            f"{current_url}"
        )

        try:

            page = crawl_page(
                current_url
            )

            final_url = normalize_url(
                page.get(
                    "url",
                    current_url
                )
            )

            if final_url in crawled_urls:

                print(
                    f"[SearchPilot] Duplicate redirect "
                    f"skipped: {final_url}"
                )

                continue

            visited.add(
                final_url
            )

            crawled_urls.add(
                final_url
            )

            results.append(
                page
            )

            # =================================================
            # DISCOVER INTERNAL LINKS
            # =================================================

            internal_links = (
                page
                .get("links", {})
                .get("internal_urls", [])
            )

            for link in internal_links:

                link = normalize_url(
                    link
                )

                if link in visited:
                    continue

                if link in crawled_urls:
                    continue

                if link in queued:
                    continue

                if not is_crawlable_url(
                    link,
                    target_hostname
                ):
                    continue

                if has_robots and not rp.can_fetch("SearchPilotBot", link):
                    continue

                # Only use internal links as fallback
                # after sitemap URLs have already been queued.
                queued.add(
                    link
                )

                queue.append(
                    link
                )

        except requests.RequestException as error:

            print(
                f"[SearchPilot] Failed: "
                f"{current_url} -> {error}"
            )

            status_code = 0
            if hasattr(error, 'response') and error.response is not None:
                status_code = error.response.status_code

            crawled_urls.add(current_url)
            results.append({
                "url": current_url,
                "status_code": status_code,
                "error": str(error)
            })

        except Exception as error:

            print(
                f"[SearchPilot] Error: "
                f"{current_url} -> {error}"
            )

            crawled_urls.add(current_url)
            results.append({
                "url": current_url,
                "status_code": 0,
                "error": str(error)
            })

    print(
        f"[SearchPilot] Crawl complete. "
        f"Crawled {len(results)} unique pages."
    )

    return results