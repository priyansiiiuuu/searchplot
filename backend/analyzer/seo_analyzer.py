from urllib.parse import urlparse
import re


# ============================================================
# KEYWORD FILTERS
# ============================================================

STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "from",
    "you", "your", "are", "was", "were", "have", "has",
    "had", "not", "but", "they", "their", "there", "what",
    "when", "where", "which", "who", "how", "why", "will",
    "would", "could", "should", "can", "about", "into",
    "than", "then", "them", "these", "those", "our", "out",
    "all", "more", "some", "any", "one", "two", "also",
    "only", "other", "its", "it's", "been", "being", "over",
    "under", "after", "before", "between", "through",
    "during", "such", "very", "www", "http", "https",
    "com", "org", "net", "home", "page", "menu", "search",
    "login", "sign", "read", "edit", "view", "main",
    "content", "article", "articles", "new", "use", "used",
    "using", "get", "got", "make", "made", "may", "must",
    "like", "just", "well", "back", "see", "now",
    "way", "many", "much", "first", "last", "next",
    "including", "include", "includes", "without", "within",
    "based", "large", "largest", "best", "free", "today",
    "learn", "learned", "start", "started", "help", "helps",
    "provide", "provides", "getting", "power", "online",
    "website", "web", "site"
}


GENERIC_SEO_TERMS = {
    "seo", "search", "engine", "optimization", "marketing",
    "digital", "business", "tool", "tools", "software",
    "service", "services", "platform", "solution", "solutions",
    "product", "products", "company", "companies",
    "information", "resource", "resources", "data", "link",
    "links", "brand", "authority", "local", "content",
    "page", "pages"
}


NAVIGATION_TERMS = {
    "menu", "login", "signup", "signin", "sign", "read",
    "view", "home", "account", "privacy", "cookie",
    "cookies", "terms", "contact"
}


# ============================================================
# HELPERS
# ============================================================

def clean_keyword(keyword: str) -> str:
    keyword = keyword.lower().strip()

    keyword = re.sub(r"\s+", " ", keyword)

    keyword = keyword.strip(" .,!?;:'\"()[]{}")

    return keyword


def is_useful_keyword(keyword: str) -> bool:
    keyword = clean_keyword(keyword)

    if not keyword:
        return False

    words = keyword.split()

    if len(keyword) < 4:
        return False

    if all(word in STOP_WORDS for word in words):
        return False

    if len(words) == 1 and keyword in GENERIC_SEO_TERMS:
        return False

    if len(words) == 1 and keyword in STOP_WORDS:
        return False

    return True


def extract_brand_terms(url: str, title: str) -> set:
    terms = set()

    parsed = urlparse(url)

    domain = parsed.netloc.lower()

    domain = domain.replace("www.", "")

    domain_name = domain.split(".")[0]

    if domain_name:
        terms.add(domain_name)

    title_words = re.findall(
        r"\b[a-zA-Z][a-zA-Z0-9'-]{2,}\b",
        title.lower()
    )

    for word in title_words:
        if (
            word not in STOP_WORDS
            and word not in GENERIC_SEO_TERMS
            and len(word) >= 4
        ):
            terms.add(word)

    return terms


def keyword_relevance(
    keyword: str,
    count: int,
    density: float
) -> float:

    words = keyword.split()

    score = 0

    # Frequency
    score += min(count * 2, 20)

    # Specific phrases are generally more useful
    if len(words) == 2:
        score += 8
    elif len(words) >= 3:
        score += 12

    # Reasonable density
    if 0.2 <= density <= 3:
        score += 5

    # Specificity
    if len(keyword) >= 8:
        score += 3

    return score


def add_issue(
    issues: list,
    issue_type: str,
    category: str,
    message: str,
    recommendation: str
):
    issues.append({
        "type": issue_type,
        "category": category,
        "message": message,
        "recommendation": recommendation
    })


# ============================================================
# MAIN SEO ANALYZER
# ============================================================

def analyze_seo(data: dict) -> dict:

    score = 100

    issues = []
    passed = []

    seo = data.get("seo", {})
    content = data.get("content", {})
    links = data.get("links", {})

    # ========================================================
    # EXTRACT DATA
    # ========================================================

    title = seo.get(
        "title", {}
    ).get(
        "value", ""
    ).strip()

    description = seo.get(
        "meta_description", {}
    ).get(
        "value", ""
    ).strip()

    h1_data = seo.get(
        "h1", {}
    )

    h1 = h1_data.get(
        "values",
        []
    )

    h1_count = h1_data.get(
        "count",
        len(h1)
    )

    h2 = content.get(
        "headings",
        {}
    ).get(
        "h2",
        []
    )

    images = seo.get(
        "images",
        {}
    )

    total_images = images.get(
        "total",
        0
    )

    missing_alt = images.get(
        "missing_alt",
        0
    )

    canonical = seo.get(
        "canonical"
    )

    robots = seo.get(
        "robots"
    )

    open_graph = seo.get(
        "open_graph",
        {}
    )

    structured_data = seo.get(
        "structured_data",
        {}
    )

    word_count = content.get(
        "word_count",
        0
    )

    internal_links = links.get(
        "internal",
        0
    )

    external_links = links.get(
        "external",
        0
    )

    url = data.get(
        "url",
        ""
    )

    # ========================================================
    # TITLE
    # ========================================================

    title_length = len(title)

    if not title:

        score -= 15

        add_issue(
            issues,
            "error",
            "Title",
            "Page is missing a title tag.",
            "Add a unique, descriptive title around 30–60 characters."
        )

    elif title_length < 30:

        score -= 5

        add_issue(
            issues,
            "warning",
            "Title",
            f"Title is too short ({title_length} characters).",
            "Make the title more descriptive while keeping it concise."
        )

    elif title_length > 60:

        score -= 5

        add_issue(
            issues,
            "warning",
            "Title",
            f"Title is too long ({title_length} characters).",
            "Keep the title around 30–60 characters to reduce truncation risk."
        )

    else:

        passed.append(
            "Title length is good."
        )

    # ========================================================
    # META DESCRIPTION
    # ========================================================

    description_length = len(description)

    if not description:

        score -= 15

        add_issue(
            issues,
            "error",
            "Meta Description",
            "Page is missing a meta description.",
            "Add a unique, useful description that summarizes the page."
        )

    elif description_length < 70:

        score -= 5

        add_issue(
            issues,
            "warning",
            "Meta Description",
            f"Meta description is short ({description_length} characters).",
            "Expand the description so it communicates the page value clearly."
        )

    elif description_length > 160:

        score -= 5

        add_issue(
            issues,
            "warning",
            "Meta Description",
            f"Meta description is long ({description_length} characters).",
            "Keep it around 70–160 characters to reduce truncation risk."
        )

    else:

        passed.append(
            "Meta description length is good."
        )

    # ========================================================
    # H1
    # ========================================================

    non_empty_h1 = [
        item.strip()
        for item in h1
        if isinstance(item, str) and item.strip()
    ]

    if h1_count == 0 or not non_empty_h1:

        score -= 15

        add_issue(
            issues,
            "error",
            "H1",
            "Page has no usable H1 heading.",
            "Add one clear H1 that describes the main purpose of the page."
        )

    elif h1_count > 1:

        score -= 5

        add_issue(
            issues,
            "warning",
            "H1",
            f"Page has {h1_count} H1 headings.",
            "Use one primary H1 and use H2/H3 elements for supporting sections."
        )

    else:

        passed.append(
            "Page has exactly one H1 heading."
        )

    # ========================================================
    # H2
    # ========================================================

    if len(h2) == 0:

        score -= 3

        add_issue(
            issues,
            "warning",
            "Headings",
            "Page has no H2 headings.",
            "Use H2 headings where appropriate to organize substantial sections."
        )

    else:

        passed.append(
            f"Page contains {len(h2)} H2 headings."
        )

    # ========================================================
    # IMAGES
    # ========================================================

    if total_images > 0:

        alt_coverage = (
            ((total_images - missing_alt) / total_images) * 100
        )

        if missing_alt > 0:

            score -= min(
                missing_alt * 2,
                10
            )

            add_issue(
                issues,
                "warning",
                "Images",
                (
                    f"{missing_alt} of {total_images} image(s) "
                    f"are missing alt text "
                    f"({alt_coverage:.0f}% coverage)."
                ),
                (
                    "Add concise, descriptive alt text to meaningful "
                    "images. Decorative images can use an empty alt attribute."
                )
            )

        else:

            passed.append(
                "All images have alt text."
            )

    else:

        passed.append(
            "Page contains no images requiring alt text."
        )

    # ========================================================
    # CANONICAL
    # ========================================================

    if not canonical:

        score -= 5

        add_issue(
            issues,
            "warning",
            "Canonical",
            "Page is missing a canonical URL.",
            "Add a canonical URL that represents the preferred version of the page."
        )

    else:

        canonical_parsed = urlparse(canonical)
        page_parsed = urlparse(url)

        if canonical_parsed.scheme not in ("http", "https"):

            score -= 5

            add_issue(
                issues,
                "warning",
                "Canonical",
                "Canonical URL uses an invalid URL scheme.",
                "Use a valid absolute HTTP or HTTPS canonical URL."
            )

        elif (
            canonical_parsed.netloc
            and page_parsed.netloc
            and canonical_parsed.netloc.lower()
            != page_parsed.netloc.lower()
        ):

            score -= 5

            add_issue(
                issues,
                "warning",
                "Canonical",
                "Canonical URL points to a different hostname.",
                "Verify that the cross-domain canonical is intentional."
            )

        else:

            passed.append(
                "Canonical URL is present."
            )

    # ========================================================
    # ROBOTS / INDEXING
    # ========================================================

    robots_lower = (
        robots.lower()
        if isinstance(robots, str)
        else ""
    )

    robot_directives = {
        directive.strip().lower()
        for directive in robots_lower.split(",")
        if directive.strip()
    }

    if "noindex" in robot_directives:

        score -= 10

        add_issue(
            issues,
            "error",
            "Indexing",
            "Page contains a noindex directive.",
            (
                "Remove noindex if this page is intended to appear "
                "in search engine results."
            )
        )

    elif "none" in robot_directives:

        score -= 10

        add_issue(
            issues,
            "error",
            "Indexing",
            "Page uses the robots 'none' directive.",
            (
                "Remove the 'none' directive if the page should be "
                "indexed and its links followed."
            )
        )

    else:

        passed.append(
            "Page is not blocked by a noindex directive."
        )

    # ========================================================
    # OPEN GRAPH
    # ========================================================

    if not open_graph:

        score -= 3

        add_issue(
            issues,
            "warning",
            "Social",
            "Open Graph metadata is missing.",
            "Add Open Graph metadata so shared links have better previews."
        )

    else:

        required_og = {
            "og:title",
            "og:description",
            "og:image",
            "og:url"
        }

        present_og = {
            key
            for key, value in open_graph.items()
            if isinstance(value, str) and value.strip()
        }

        missing_og = sorted(
            required_og - present_og
        )

        if missing_og:

            score -= min(
                len(missing_og),
                3
            )

            add_issue(
                issues,
                "warning",
                "Social",
                (
                    "Open Graph metadata is incomplete. "
                    f"Missing: {', '.join(missing_og)}."
                ),
                (
                    "Add the missing Open Graph properties to improve "
                    "social sharing previews."
                )
            )

        else:

            passed.append(
                "Core Open Graph metadata is present."
            )

    # ========================================================
    # STRUCTURED DATA
    # ========================================================

    structured_data_count = structured_data.get(
        "count",
        0
    )

    if structured_data_count > 0:

        passed.append(
            f"Page contains {structured_data_count} structured data block(s)."
        )

    else:

        add_issue(
            issues,
            "info",
            "Structured Data",
            "No JSON-LD structured data was detected.",
            (
                "Consider adding relevant Schema.org structured data "
                "where it matches the page content."
            )
        )

    # ========================================================
    # CONTENT
    # ========================================================

    if word_count < 100:

        score -= 8

        add_issue(
            issues,
            "warning",
            "Content",
            f"Page contains only {word_count} words of visible content.",
            (
                "Review whether the page provides enough useful content "
                "to satisfy its search intent."
            )
        )

    elif word_count < 300:

        score -= 5

        add_issue(
            issues,
            "warning",
            "Content",
            f"Page contains {word_count} words of visible content.",
            (
                "Consider whether additional useful content is needed. "
                "Word count alone does not determine search performance."
            )
        )

    else:

        passed.append(
            f"Page has {word_count} words of visible content."
        )

    # ========================================================
    # LINKS
    # ========================================================

    total_links = internal_links + external_links

    if total_links == 0:

        score -= 5

        add_issue(
            issues,
            "warning",
            "Links",
            "Page contains no crawlable links.",
            "Add relevant internal links where they improve navigation and discovery."
        )

    else:

        passed.append(
            f"Page contains {total_links} links "
            f"({internal_links} internal, {external_links} external)."
        )

    if internal_links == 0:

        score -= 3

        add_issue(
            issues,
            "warning",
            "Internal Links",
            "Page has no internal links.",
            (
                "Add relevant internal links where appropriate to help "
                "users and search engines discover related content."
            )
        )
    else:

        passed.append(
            f"Page contains {internal_links} internal link(s)."
        )

    # ========================================================
    # HTTPS
    # ========================================================

    parsed_url = urlparse(url)

    if parsed_url.scheme != "https":

        score -= 5

        add_issue(
            issues,
            "warning",
            "Security",
            "Website is not using HTTPS.",
            "Use HTTPS to protect visitors and secure connections."
        )

    else:

        passed.append(
            "Website is using HTTPS."
        )

    # ========================================================
    # KEYWORD INTELLIGENCE
    # ========================================================

    keywords = content.get(
        "keywords",
        []
    )

    keyword_analysis = []

    title_lower = title.lower()
    description_lower = description.lower()

    h1_text = " ".join(
        non_empty_h1
    ).lower()

    brand_terms = extract_brand_terms(
        url,
        title
    )

    for item in keywords[:30]:

        keyword = clean_keyword(
            item.get(
                "keyword",
                ""
            )
        )

        count = item.get(
            "count",
            0
        )

        density = item.get(
            "density",
            0
        )

        if not is_useful_keyword(keyword):
            continue

        words = keyword.split()

        # Avoid obvious branded/domain terms
        if len(words) == 1 and keyword in brand_terms:
            continue

        # Avoid navigation/UI phrases
        if any(
            word in NAVIGATION_TERMS
            for word in words
        ):
            continue

        in_title = keyword in title_lower
        in_h1 = keyword in h1_text
        in_description = keyword in description_lower

        placement_count = sum([
            in_title,
            in_h1,
            in_description
        ])

        opportunity = (
            count >= 3
            and placement_count == 0
            and len(keyword) >= 5
        )

        stuffing_warning = (
            density >= 5
        )

        relevance = keyword_relevance(
            keyword,
            count,
            density
        )

        keyword_analysis.append({
            "keyword": keyword,
            "count": count,
            "density": density,
            "in_title": in_title,
            "in_h1": in_h1,
            "in_meta_description": in_description,
            "opportunity": opportunity,
            "stuffing_warning": stuffing_warning,
            "relevance": relevance
        })

    # ========================================================
    # RANK KEYWORDS
    # ========================================================

    keyword_analysis.sort(
        key=lambda item: (
            item["relevance"],
            item["count"]
        ),
        reverse=True
    )

    keyword_analysis = keyword_analysis[:20]

    # ========================================================
    # OPPORTUNITIES
    # ========================================================

    opportunities = [
        item
        for item in keyword_analysis
        if item["opportunity"]
    ]

    opportunities.sort(
        key=lambda item: (
            item["relevance"],
            item["count"]
        ),
        reverse=True
    )

    # ========================================================
    # KEYWORD STUFFING
    # ========================================================

    stuffing_warnings = [
        item
        for item in keyword_analysis
        if item["stuffing_warning"]
    ]

    # ========================================================
    # KEYWORD ISSUES
    # ========================================================

    if opportunities:

        add_issue(
            issues,
            "warning",
            "Keyword Opportunity",
            (
                f"{len(opportunities)} relevant keyword(s) appear "
                "frequently in the content but are missing from the "
                "title, H1 and meta description."
            ),
            (
                "Consider naturally incorporating the strongest "
                "relevant terms into important SEO elements. "
                "Do not force keywords where they do not fit."
            )
        )

    if stuffing_warnings:

        add_issue(
            issues,
            "warning",
            "Keyword Stuffing",
            (
                f"{len(stuffing_warnings)} keyword(s) have "
                "unusually high density."
            ),
            (
                "Avoid repetitive keyword usage. Prioritize natural, "
                "readable content and topic coverage."
            )
        )

    # ========================================================
    # REMOVE INTERNAL RELEVANCE FIELD
    # ========================================================

    for item in keyword_analysis:
        item.pop(
            "relevance",
            None
        )

    # Also remove internal relevance from opportunities
    for item in opportunities:
        item.pop(
            "relevance",
            None
        )

    # ========================================================
    # FINAL SCORE
    # ========================================================

    score = max(
        0,
        min(
            score,
            100
        )
    )

    if score >= 90:
        grade = "Excellent"

    elif score >= 75:
        grade = "Good"

    elif score >= 50:
        grade = "Needs Improvement"

    else:
        grade = "Poor"

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "score": score,
        "grade": grade,
        "issues": issues,
        "passed": passed,
        "keyword_analysis": keyword_analysis,
        "keyword_opportunities": opportunities,
        "keyword_stuffing_warnings": stuffing_warnings
    }