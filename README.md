# SIH 2026 — Problem Statement Leaderboard & Analytics

A real-time telemetry dashboard and analytics explorer for Smart India Hackathon 2026 Problem Statements. Features live submission counts, estimated win probabilities, competition grading, and multi-track filtering.

---

## Features

- **Live Telemetry Dashboard**: Executive metrics covering total problem statements, Software vs Hardware split, peak competition, and hidden gems (< 5 submissions).
- **Estimated Win Odds**: Algorithmic conversion probability calculated dynamically from team density.
- **Categorization & Filtering**:
  - 17 Themes & Tracks (Smart Automation, Blockchain, Agriculture, MedTech, Disaster Management, etc.)
  - Software Only vs Hardware Only
  - Top 10 Most Popular (High Traffic)
  - Least Submissions (Hidden Gems / High Win Odds)
  - AI / ML & DeepTech
- **Interactive Bookmarks / Shortlist**: Shortlist problem statements with persistence in browser localStorage.
- **Dual Layouts**: Dense Table View and Grid Cards View.
- **Full Detail Modal**: Inspect complete problem descriptions, backgrounds, expected solutions, and sponsoring ministries.

---

## Repository Structure

```
├── .github/
│   └── workflows/
│       └── update_data.yml     # Automated scheduled scraping workflow
├── data/
│   ├── sih_ps_ranked.csv       # Tabular dataset export
│   └── sih_ps_ranked.json      # Complete JSON dataset with full descriptions
├── scripts/
│   ├── sih_ps_ranker.py        # Anti-bot Selenium scraper script
│   └── update_dashboard.py     # Dashboard compiler script
├── extra/                      # Offline samples, mockups, and reference files (git-ignored)
├── .gitignore                  # Ignores local artifacts and extra directory
├── index.html                  # Self-contained, responsive dashboard website
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

