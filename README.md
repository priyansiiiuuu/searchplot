# SearchPilot

A full-stack SEO auditing platform that analyzes web pages and websites for technical, on-page, and content-related SEO issues.

## Live Demo

**Frontend:** https://searchplot.onrender.com

**Backend API:** https://searchplot-api.onrender.com

## Features

- Single-page SEO audits
- Full website crawling
- SEO score out of 100
- Title and meta description analysis
- H1/H2 heading checks
- Image alt-text analysis
- Canonical URL checks
- Robots.txt and sitemap detection
- Open Graph metadata checks
- Structured data detection
- Internal and external link analysis
- Content and word-count analysis
- Keyword analysis and stuffing detection
- Actionable SEO recommendations
- Site-wide score and issue summaries

## Tech Stack

**Frontend**
- React
- Vite
- JavaScript
- CSS

**Backend**
- Python
- FastAPI
- Uvicorn
- Requests
- BeautifulSoup
- Pydantic

**Deployment**
- Render
- GitHub

## Architecture

```text
React Frontend
      │
      │ HTTP / JSON
      ▼
FastAPI Backend
      │
      ├── Web Crawler
      │     ├── HTML parsing
      │     ├── Links
      │     ├── Robots.txt
      │     └── Sitemaps
      │
      └── SEO Analyzer
            ├── SEO scoring
            ├── Technical checks
            ├── Content analysis
            └── Keyword analysis
## Testing

Run the backend test suite with:

```bash
python3 -m pytest -q tests/test_backend.py
```
