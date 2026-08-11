from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from urllib.parse import urlparse
import requests
import os
from dotenv import load_dotenv

from crawler.crawler import crawl_page, crawl_site, is_safe_url
from analyzer.seo_analyzer import analyze_seo

# Load environment variables
load_dotenv()

app = FastAPI(title="SearchPilot API")


# =========================================================
# CORS
# =========================================================

cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

# Sanitize origins to prevent credentials errors if wildcard is provided
if "*" in origins:
    origins = [o for o in origins if o != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# GLOBAL ERROR HANDLER
# =========================================================

@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    print(f"[Unhandled Server Error] {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal server error occurred."}
    )


# =========================================================
# REQUEST MODEL
# =========================================================

class CrawlRequest(BaseModel):
    url: str


# =========================================================
# URL VALIDATION
# =========================================================

def validate_url(url: str):

    url = url.strip()

    if not url:
        raise HTTPException(
            status_code=400,
            detail="Please enter a URL."
        )

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="URL must start with http:// or https://."
        )

    if not parsed.netloc:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid website URL."
        )

    # Validate destination host is safe and not resolving to private IP or loopback (SSRF protection)
    if not is_safe_url(url):
        raise HTTPException(
            status_code=400,
            detail="Access to the specified URL is blocked for security reasons (private IP or loopback)."
        )

    return url


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "SearchPilot API is running"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# =========================================================
# SINGLE PAGE ANALYSIS
# =========================================================

@app.post("/crawl")
def crawl(request: CrawlRequest):

    url = validate_url(request.url)

    try:

        crawl_data = crawl_page(url)

        seo_analysis = analyze_seo(crawl_data)

        return {
            "success": True,
            "crawl": crawl_data,
            "seo_analysis": seo_analysis
        }

    except requests.exceptions.Timeout:

        raise HTTPException(
            status_code=400,
            detail=(
                "The website took too long to respond. "
                "Please try again later."
            )
        )

    except requests.exceptions.ConnectionError:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to reach this website. "
                "Check that the URL is correct and publicly accessible."
            )
        )

    except requests.exceptions.HTTPError as error:

        status_code = (
            error.response.status_code
            if error.response is not None
            else None
        )

        if status_code:

            message = (
                f"The website returned an HTTP {status_code} error."
            )

        else:

            message = (
                "The website could not be accessed."
            )

        raise HTTPException(
            status_code=400,
            detail=message
        )

    except requests.exceptions.RequestException:

        raise HTTPException(
            status_code=400,
            detail=(
                "SearchPilot could not access this website. "
                "Make sure the URL is valid and publicly accessible."
            )
        )

    except Exception as error:

        print(
            f"[SearchPilot] Crawl error for {url}: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred while "
                "analyzing this website."
            )
        )


# =========================================================
# FULL SITE CRAWL
# =========================================================

@app.post("/site-crawl")
def site_crawl(request: CrawlRequest):

    url = validate_url(request.url)

    try:

        pages = crawl_site(
            url,
            max_pages=20
        )

    except requests.exceptions.Timeout:

        raise HTTPException(
            status_code=400,
            detail=(
                "The website took too long to respond "
                "during the site crawl."
            )
        )

    except requests.exceptions.ConnectionError:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to reach this website. "
                "Check that the URL is correct and publicly accessible."
            )
        )

    except requests.exceptions.RequestException:

        raise HTTPException(
            status_code=400,
            detail=(
                "SearchPilot could not access this website."
            )
        )

    except Exception as error:

        print(
            f"[SearchPilot] Site crawl error for {url}: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred "
                "during the site crawl."
            )
        )


    # =====================================================
    # ANALYZE CRAWLED PAGES
    # =====================================================

    analyzed_pages = []

    # Site-wide issue counters
    issue_summary = {
        "missing_title": 0,
        "short_title": 0,
        "long_title": 0,

        "missing_meta_description": 0,
        "short_meta_description": 0,
        "long_meta_description": 0,

        "missing_h1": 0,
        "multiple_h1": 0,
        "missing_h2": 0,

        "missing_canonical": 0,
        "noindex": 0,

        "missing_open_graph": 0,
        "missing_structured_data": 0,

        "missing_alt_text": 0,
        "low_content": 0,

        "no_internal_links": 0,
        "no_links": 0,

        "non_https": 0,

        "keyword_opportunities": 0,
        "keyword_stuffing": 0
    }


    # =====================================================
    # ANALYZE EVERY PAGE
    # =====================================================

    for page in pages:

        # Record failed pages
        if "error" in page:
            analyzed_pages.append({
                "url": page.get("url", ""),
                "title": "Failed to Crawl Page",
                "score": 0,
                "grade": "Failed",
                "issues": 1,
                "status_code": page.get("status_code", 0),
                "error": page.get("error", "Unknown error")
            })
            continue

        try:

            seo_analysis = analyze_seo(page)

            issues = seo_analysis.get(
                "issues",
                []
            )

            # ---------------------------------------------
            # COUNT ISSUE TYPES
            # ---------------------------------------------

            for issue in issues:

                category = issue.get(
                    "category",
                    ""
                )

                if category == "Title":

                    message = issue.get(
                        "message",
                        ""
                    ).lower()

                    if "missing" in message:
                        issue_summary["missing_title"] += 1

                    elif "too short" in message:
                        issue_summary["short_title"] += 1

                    elif "too long" in message:
                        issue_summary["long_title"] += 1


                elif category == "Meta Description":

                    message = issue.get(
                        "message",
                        ""
                    ).lower()

                    if "missing" in message:
                        issue_summary[
                            "missing_meta_description"
                        ] += 1

                    elif "short" in message:
                        issue_summary[
                            "short_meta_description"
                        ] += 1

                    elif "long" in message:
                        issue_summary[
                            "long_meta_description"
                        ] += 1


                elif category == "H1":

                    message = issue.get(
                        "message",
                        ""
                    ).lower()

                    if "no h1" in message:
                        issue_summary["missing_h1"] += 1

                    elif "multiple" in message:
                        issue_summary["multiple_h1"] += 1


                elif category == "Headings":

                    issue_summary["missing_h2"] += 1


                elif category == "Canonical":

                    issue_summary["missing_canonical"] += 1


                elif category == "Indexing":

                    issue_summary["noindex"] += 1


                elif category == "Social":

                    issue_summary["missing_open_graph"] += 1


                elif category == "Images":

                    issue_summary["missing_alt_text"] += 1


                elif category == "Content":

                    issue_summary["low_content"] += 1


                elif category == "Links":

                    issue_summary["no_links"] += 1


                elif category == "Internal Links":

                    issue_summary["no_internal_links"] += 1


                elif category == "Security":

                    issue_summary["non_https"] += 1


                elif category == "Keyword Opportunity":

                    issue_summary[
                        "keyword_opportunities"
                    ] += 1


                elif category == "Keyword Stuffing":

                    issue_summary[
                        "keyword_stuffing"
                    ] += 1


            # ---------------------------------------------
            # STRUCTURED DATA
            # ---------------------------------------------

            structured_data = (
                page
                .get("seo", {})
                .get("structured_data", {})
            )

            if not structured_data.get(
                "exists",
                False
            ):

                issue_summary[
                    "missing_structured_data"
                ] += 1


            # ---------------------------------------------
            # PAGE RESULT
            # ---------------------------------------------

            analyzed_pages.append({

                "url": page.get(
                    "url",
                    ""
                ),

                "title": (
                    page
                    .get("seo", {})
                    .get("title", {})
                    .get("value", "")
                ),

                "score": seo_analysis.get(
                    "score",
                    0
                ),

                "grade": seo_analysis.get(
                    "grade",
                    "Poor"
                ),

                "issues": len(issues),

                "status_code": page.get(
                    "status_code",
                    0
                )

            })

        except Exception as error:

            print(
                f"[SearchPilot] Analysis failed "
                f"for {page.get('url')}: {error}"
            )

            continue


    # =====================================================
    # SITE STATISTICS
    # =====================================================

    scores = [
        page["score"]
        for page in analyzed_pages
        if isinstance(
            page.get("score"),
            (int, float)
        )
    ]


    # Average score
    average_score = (
        round(
            sum(scores) / len(scores),
            1
        )
        if scores
        else 0
    )


    # Highest score
    highest_score = (
        max(scores)
        if scores
        else 0
    )


    # Lowest score
    lowest_score = (
        min(scores)
        if scores
        else 0
    )


    # Pages with issues
    pages_with_issues = sum(
        1
        for page in analyzed_pages
        if page.get(
            "issues",
            0
        ) > 0
    )


    # Good pages
    good_pages = sum(
        1
        for page in analyzed_pages
        if page.get(
            "score",
            0
        ) >= 75
    )


    # Pages needing attention
    needs_attention = sum(
        1
        for page in analyzed_pages
        if page.get(
            "score",
            0
        ) < 75
    )


    # =====================================================
    # WORST PAGES
    # =====================================================

    worst_pages = sorted(
        analyzed_pages,
        key=lambda page: page.get(
            "score",
            0
        )
    )[:5]


    # =====================================================
    # BEST PAGES
    # =====================================================

    best_pages = sorted(
        analyzed_pages,
        key=lambda page: page.get(
            "score",
            0
        ),
        reverse=True
    )[:5]


    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    return {

        "success": True,

        "url": url,

        "pages_crawled": len(
            analyzed_pages
        ),

        "average_score": average_score,

        "highest_score": highest_score,

        "lowest_score": lowest_score,

        "pages_with_issues": pages_with_issues,

        "good_pages": good_pages,

        "needs_attention": needs_attention,

        "issue_summary": issue_summary,

        "worst_pages": worst_pages,

        "best_pages": best_pages,

        "pages": analyzed_pages
    }