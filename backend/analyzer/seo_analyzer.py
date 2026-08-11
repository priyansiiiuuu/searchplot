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
    "like", "just", "well", "back", "see", "see", "now",
    "way", "many", "much", "first", "last", "next",
    "including", "include", "includes", "without", "within",
    "based", "large", "largest", "best", "free", "today",
    "learn", "learned", "start", "started", "help", "helps",
    "provide", "provides", "get", "getting", "power",
    "new", "online", "website", "web", "site"
}


GENERIC_SEO_TERMS = {
    "seo",
    "search",
    "engine",
    "optimization",
    "marketing",
    "digital",
    "business",
    "tool",
    "tools",
    "software",
    "service",
    "services",
    "platform",
    "solution",
    "solutions",
    "product",
    "products",
    "company",
    "companies",
    "information",
    "resource",
    "resources",
    "data",
    "link",
    "links",
    "brand",
    "authority",
    "local",
    "content",
    "page",
    "pages"
}


# ============================================================
# HELPERS
# ============================================================

def clean_keyword(keyword: str) -> str:

    keyword = keyword.lower().strip()

    keyword = re.sub(
        r"\s+",
        " ",
        keyword
    )

    keyword = keyword.strip(
        " .,!?;:'\"()[]{}"
    )

    return keyword


def is_useful_keyword(keyword: str) -> bool:

    keyword = clean_keyword(keyword)

    if not keyword:
        return False

    words = keyword.split()

    # Ignore very short terms
    if len(keyword) < 4:
        return False

    # Ignore terms consisting entirely of stop words
    if all(word in STOP_WORDS for word in words):
        return False

    # Ignore generic single-word SEO terminology
    if len(words) == 1 and keyword in GENERIC_SEO_TERMS:
        return False

    # Ignore single-word stop words
    if len(words) == 1 and keyword in STOP_WORDS:
        return False

    return True


def extract_brand_terms(url: str, title: str) -> set:

    terms = set()

    parsed = urlparse(url)

    domain = parsed.netloc.lower()

    domain = domain.replace(
        "www.",
        ""
    )

    domain_name = domain.split(".")[0]

    if domain_name:
        terms.add(domain_name)

    title_words = re.findall(
        r"\b[a-zA-Z][a-zA-Z0-9'-]{2,}\b",
        title.lower()
    )

    # Words from the title that look like brand names.
    # We only use this as a soft filter.
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

    # Multi-word phrases are generally more useful
    if len(words) == 2:
        score += 8

    elif len(words) >= 3:
        score += 12

    # Reasonable density gets a small boost
    if 0.2 <= density <= 3:
        score += 5

    # Longer specific terms get a small boost
    if len(keyword) >= 8:
        score += 3

    return score


# ============================================================
# MAIN SEO ANALYZER
# ============================================================

def analyze_seo(data: dict) -> dict:

    score = 100

    issues = []
    passed = []

    seo = data.get(
        "seo",
        {}
    )

    content = data.get(
        "content",
        {}
    )

    links = data.get(
        "links",
        {}
    )

    title = seo.get(
        "title",
        {}
    ).get(
        "value",
        ""
    )

    description = seo.get(
        "meta_description",
        {}
    ).get(
        "value",
        ""
    )

    h1 = seo.get(
        "h1",
        {}
    ).get(
        "values",
        []
    )

    h1_count = seo.get(
        "h1",
        {}
    ).get(
        "count",
        0
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

        issues.append({
            "type": "error",
            "category": "Title",
            "message": "Page is missing a title tag.",
            "recommendation": (
                "Add a unique title between 30–60 characters."
            )
        })

    elif title_length < 30:

        score -= 5

        issues.append({
            "type": "warning",
            "category": "Title",
            "message": (
                f"Title is too short "
                f"({title_length} characters)."
            ),
            "recommendation": (
                "Make the title more descriptive."
            )
        })

    elif title_length > 60:

        score -= 5

        issues.append({
            "type": "warning",
            "category": "Title",
            "message": (
                f"Title is too long "
                f"({title_length} characters)."
            ),
            "recommendation": (
                "Keep the title around 30–60 characters."
            )
        })

    else:

        passed.append(
            "Title length is good."
        )

    # ========================================================
    # META DESCRIPTION
    # ========================================================

    description_length = len(
        description
    )

    if not description:

        score -= 15

        issues.append({
            "type": "error",
            "category": "Meta Description",
            "message": (
                "Page is missing a meta description."
            ),
            "recommendation": (
                "Add a descriptive meta description."
            )
        })

    elif description_length < 70:

        score -= 5

        issues.append({
            "type": "warning",
            "category": "Meta Description",
            "message": (
                f"Meta description is short "
                f"({description_length} characters)."
            ),
            "recommendation": (
                "Expand the description."
            )
        })

    elif description_length > 160:

        score -= 5

        issues.append({
            "type": "warning",
            "category": "Meta Description",
            "message": (
                f"Meta description is long "
                f"({description_length} characters)."
            ),
            "recommendation": (
                "Keep it below approximately 160 characters."
            )
        })

    else:

        passed.append(
            "Meta description length is good."
        )

    # ========================================================
    # H1
    # ========================================================

    if h1_count == 0:

        score -= 15

        issues.append({
            "type": "error",
            "category": "H1",
            "message": (
                "Page has no H1 heading."
            ),
            "recommendation": (
                "Add one clear H1 describing the page."
            )
        })

    elif h1_count > 1:

        score -= 5

        issues.append({
            "type": "warning",
            "category": "H1",
            "message": (
                f"Page has {h1_count} H1 headings."
            ),
            "recommendation": (
                "Use one primary H1."
            )
        })

    else:

        passed.append(
            "Page has exactly one H1 heading."
        )

    # ========================================================
    # H2
    # ========================================================

    if len(h2) == 0:

        score -= 3

        issues.append({
            "type": "warning",
            "category": "Headings",
            "message": (
                "Page has no H2 headings."
            ),
            "recommendation": (
                "Use H2 headings to structure the content."
            )
        })

    else:

        passed.append(
            f"Page contains {len(h2)} H2 headings."
        )

    # ========================================================
    # IMAGES
    # ========================================================

    if total_images > 0 and missing_alt > 0:

        score -= min(
            missing_alt * 2,
            10
        )

        issues.append({
            "type": "warning",
            "category": "Images",
            "message": (
                f"{missing_alt} image(s) are missing alt text."
            ),
            "recommendation": (
                "Add concise, descriptive alt text to "
                "meaningful images."
            )
        })

    elif total_images > 0:

        passed.append(
            "All images have alt text."
        )

    # ========================================================
    # CANONICAL
    # ========================================================

    if not canonical:

        score -= 5

        issues.append({
            "type": "warning",
            "category": "Canonical",
            "message": (
                "Page is missing a canonical URL."
            ),
            "recommendation": (
                "Add a canonical URL."
            )
        })

    else:

        passed.append(
            "Canonical URL is present."
        )

    # ========================================================
    # ROBOTS
    # ========================================================

    if robots and "noindex" in robots.lower():

        score -= 10

        issues.append({
            "type": "error",
            "category": "Indexing",
            "message": (
                "Page contains a noindex directive."
            ),
            "recommendation": (
                "Remove noindex if the page should "
                "appear in search results."
            )
        })

    else:

        passed.append(
            "Page is not blocked by a noindex directive."
        )

    # ========================================================
    # OPEN GRAPH
    # ========================================================

    if not open_graph:

        score -= 3

        issues.append({
            "type": "warning",
            "category": "Social",
            "message": (
                "Open Graph metadata is missing."
            ),
            "recommendation": (
                "Add Open Graph metadata."
            )
        })

    else:

        passed.append(
            "Open Graph metadata is present."
        )

    # ========================================================
    # CONTENT
    # ========================================================

    if word_count < 300:

        score -= 5

        issues.append({
            "type": "warning",
            "category": "Content",
            "message": (
                f"Page contains only {word_count} words."
            ),
            "recommendation": (
                "Add more useful, relevant content."
            )
        })

    else:

        passed.append(
            f"Page has {word_count} words of content."
        )

    # ========================================================
    # LINKS
    # ========================================================

    total_links = (
        internal_links +
        external_links
    )

    if total_links == 0:

        score -= 5

        issues.append({
            "type": "warning",
            "category": "Links",
            "message": (
                "Page contains no links."
            ),
            "recommendation": (
                "Add relevant internal and external links."
            )
        })

    else:

        passed.append(
            f"Page contains {total_links} links "
            f"({internal_links} internal, "
            f"{external_links} external)."
        )

    if internal_links == 0:

        score -= 3

        issues.append({
            "type": "warning",
            "category": "Internal Links",
            "message": (
                "Page has no internal links."
            ),
            "recommendation": (
                "Add relevant links to other pages "
                "on the website."
            )
        })

    # ========================================================
    # HTTPS
    # ========================================================

    parsed_url = urlparse(
        url
    )

    if parsed_url.scheme != "https":

        score -= 5

        issues.append({
            "type": "warning",
            "category": "Security",
            "message": (
                "Website is not using HTTPS."
            ),
            "recommendation": (
                "Use HTTPS for the website."
            )
        })

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
        h1
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

        if not is_useful_keyword(
            keyword
        ):
            continue

        words = keyword.split()

        # Ignore obvious branded/domain terms
        if len(words) == 1 and keyword in brand_terms:
            continue

        # Ignore phrases containing obvious generic navigation terms
        if any(
            word in {
                "menu",
                "login",
                "signup",
                "sign",
                "read",
                "view",
                "home"
            }
            for word in words
        ):
            continue

        in_title = (
            keyword in title_lower
        )

        in_h1 = (
            keyword in h1_text
        )

        in_description = (
            keyword in description_lower
        )

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
    # STUFFING
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

        issues.append({
            "type": "warning",
            "category": "Keyword Opportunity",
            "message": (
                f"{len(opportunities)} relevant keyword(s) "
                "appear frequently in the content but are "
                "missing from the title, H1 and meta description."
            ),
            "recommendation": (
                "Consider naturally incorporating the most "
                "relevant keywords into important SEO elements. "
                "Do not force keywords where they do not fit."
            )
        })

    if stuffing_warnings:

        issues.append({
            "type": "warning",
            "category": "Keyword Stuffing",
            "message": (
                f"{len(stuffing_warnings)} keyword(s) have "
                "unusually high density."
            ),
            "recommendation": (
                "Avoid repeating keywords unnaturally. "
                "Focus on readable, useful content."
            )
        })

    # ========================================================
    # REMOVE INTERNAL RELEVANCE FIELD FROM FRONTEND DATA
    # ========================================================

    for item in keyword_analysis:

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