# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FundSeeker is a Python CLI tool for collecting and analyzing Chinese mutual fund data from Eastmoney (天天基金网). It fetches fund rankings, ratings, detailed information, historical NAV (Net Asset Value) data, and generates investment recommendations using configurable scoring models.

**Key capabilities:**
- Fetch fund rankings with multi-agency ratings (Morningstar, Shanghai Securities, etc.)
- Collect detailed fund information including manager performance and fund scale
- Download historical NAV time series for backtesting
- Generate recommendations using basic 8-factor scoring or advanced ML models
- Support for batch processing with resume capability

## Architecture

The codebase follows a service-oriented architecture:

```
fundseeker/
├── .main.py              # Typer CLI entry point
├── fundseeker.sh/.bat    # Shell wrappers for venv management
├── config.yaml           # Configuration (weights, paths, model configs)
├── src/
│   ├── cli/              # Interactive menu system
│   ├── services/         # Business logic layer
│   │   ├── rank_service.py           # Ranking + rating fetcher
│   │   ├── detail_service.py         # Fund details with resume
│   │   ├── nav_service.py            # NAV time series downloader
│   │   ├── recommend_service.py      # Basic 8-factor scoring
│   │   └── advanced_recommend_service.py  # ML-based recommendations
│   ├── data/             # Low-level data fetchers (HTTP/parsing)
│   └── utils/            # Config, logging, I/O helpers
├── data/                 # User-editable fund lists
├── templates/            # CSV templates for fund lists
├── output/               # All generated Excel/CSV files (timestamped)
├── .fs/                  # Hidden progress tracking and logs
└── doc/                  # Requirements, design docs, user manual
```

**Data flow:**
1. Services orchestrate fetchers and handle batch processing
2. Fetchers (`src/data/`) make HTTP requests and parse responses
3. Utils provide config loading, file I/O, and logging
4. All outputs go to `output/` with timestamps; progress saved to `.fs/`

**Sister project:** `fund_reco_fit/` contains advanced feature engineering and model training using SQLite + NAV data.

## Common Commands

### Development Setup
```bash
# macOS/Linux
./fundseeker.sh              # Auto-creates venv, installs deps, launches menu

# Windows
fundseeker.bat               # Same as above

# Manual setup (if needed)
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Running Commands
```bash
# Interactive menu (recommended for first-time users)
./fundseeker.sh              # or fundseeker.bat on Windows

# Direct commands
./fundseeker.sh rank --limit 200                    # Fetch top 200 funds with ratings
./fundseeker.sh details --input data/fund_list.csv  # Fetch details for fund list
./fundseeker.sh nav                                 # Batch download NAV for all funds in list
./fundseeker.sh nav 000001 --start-date 2020-01-01  # Download NAV for specific fund
./fundseeker.sh recommend --top-n 200               # Generate basic recommendations
./fundseeker.sh recommend --mode advanced --adv-variant 6m  # Use ML model
./fundseeker.sh progress                            # Check task progress

# Using Python directly (after venv activation)
python .main.py rank --start-date 2024-01-01 --end-date 2024-12-31
python .main.py details --no-resume                 # Disable resume capability
python .main.py recommend --mode advanced --snapshot-date 2024-12-31
```

### Testing
```bash
python -m unittest discover tests    # Run all tests
python -m unittest tests.test_config # Run specific test module
```

## Key Design Patterns

### Service Layer Pattern
All business logic lives in `src/services/`. Each service:
- Takes `AppConfig` in constructor for dependency injection
- Implements a `run()` or similar method that returns output paths
- Handles batch processing, progress tracking, and error recovery
- Writes timestamped files to `output/` (never overwrites)

Example: `DetailService.run(fund_list_path, auto_resume=True)` reads the fund list, fetches details in batches of 10, saves progress every 100 records to `.fs/progress/`, and supports resume on interruption.

### Configuration Management
`config.yaml` is the single source of truth for:
- Directory paths (`output_dir`, `logs_dir`, `progress_dir`, etc.)
- HTTP settings (`request_delay`, `request_timeout`, `user_agent`)
- Recommendation weights (8 factors: recent, mid, long, risk_penalty, manager, scale, rating, age)
- Advanced model configs (db paths, feature tables, model weights)

Environment variables override config: `FUNDSEEKER_RECENT_WEIGHT=0.4` changes the recent momentum weight.

Load config via `load_config()` from `src/utils/config.py`, which returns an `AppConfig` dataclass with typed fields.

### Progress Tracking & Resume
Long-running tasks (details, bulk NAV) save progress to `.fs/progress/<task>_<timestamp>.json`:
```json
{
  "total": 10000,
  "processed": 2500,
  "last_index": 2499,
  "start_time": "2024-12-14T10:30:00",
  "last_update": "2024-12-14T11:45:00"
}
```

Services check for existing progress files and resume from `last_index + 1` unless `--no-resume` is passed.

### Output File Naming
All outputs use timestamps to prevent overwrites:
- Rankings: `output/rank_with_rating_YYYYMMDD_HHMMSS.xlsx`
- Details: `output/fund_details_YYYYMMDD_HHMMSS.xlsx`
- Recommendations: `output/recommendations_YYYYMMDD_HHMMSS.xlsx`
- NAV data: `output/nav/nav_<fund_code>.xlsx` (overwrites on re-run)

Services automatically find the latest file by sorting timestamps when merging data.

## Important Implementation Details

### Recommendation System

**Basic Mode (8-factor scoring):**
The `RecommendService` merges the latest ranking and details files, then calculates 8 normalized scores:

1. **Recent momentum** (35%): Recent returns / volatility proxy
2. **Mid-term trend** (20%): Medium-term performance
3. **Long-term stability** (15%): Long-term returns
4. **Risk penalty** (10%): Volatility-based penalty
5. **Manager score** (10%): Manager return × tenure years
6. **Scale liquidity** (5%): Fund size scoring
7. **Rating score** (30%): Average of multi-agency ratings (Morningstar, Shanghai Securities, etc.)
8. **Age score** (2%): Fund establishment date

Weights are configurable in `config.yaml` under `recommendation_weights`. The final recommendation value is a weighted sum of normalized scores (0-100 scale).

**Advanced Mode (ML-based):**
Uses features from `fund_reco_fit/data/fundseeker_nav.db` (SQLite) with trained model weights from `fund_reco_fit/models/model_params_*.json`. Supports multiple variants (6m, 12m, crosssec6, crosssec12) configured in `config.yaml` under `advanced_model`. Each variant specifies:
- `db_path`: Path to SQLite database with features
- `feature_table`: Table name (e.g., `features_M_star`)
- `weights_path`: JSON file with trained factor weights
- `top_k`: Number of top recommendations to return

Advanced mode filters funds with <36 months of NAV history and includes Morningstar-style risk metrics (36M annualized return, downside volatility, max drawdown, risk-adjusted return, peer percentile).

### Data Fetchers

**Fetcher responsibilities:**
- `ranking_fetcher.py`: Calls Eastmoney API for fund rankings (returns, volatility, Sharpe ratio)
- `rating_fetcher.py`: Scrapes rating pages for Morningstar, Shanghai Securities, etc.
- `detail_fetcher.py`: Extracts fund details (scale, inception date) and manager info (tenure, returns)
- `nav_fetcher.py`: Downloads historical NAV time series from Eastmoney

All fetchers use configurable delays (`request_delay` in config) and timeouts to avoid rate limiting.

### Batch Processing Strategy

`DetailService` processes funds in batches:
- **Batch size**: 10 funds per batch (configurable via `batch_size`)
- **Save interval**: Progress saved every 100 funds (configurable via `save_interval`)
- **Delay**: 0.5s between requests (configurable via `request_delay`)
- **Resume**: Automatically resumes from last successful index on interruption

This design balances throughput with reliability for large datasets (10,000+ funds).

## Coding Conventions

### Style Guidelines
- Follow PEP 8 with 4-space indentation
- Use snake_case for modules, functions, and variables
- Use PascalCase for classes (e.g., `RankService`, `AppConfig`)
- Prefer pathlib (`Path`) over string paths
- Type hints required for function signatures

### Service Implementation Pattern
When creating or modifying services:
1. Accept `AppConfig` in `__init__` for all configuration needs
2. Implement idempotent operations (safe to re-run)
3. Write outputs to timestamped files in `output/`
4. Use `ensure_dir()` from `io_helper` to create directories
5. Log to both console and `.fs/logs/<date>/` using the logger from `utils/logger.py`
6. Handle exceptions gracefully and provide user-friendly error messages

### File I/O Patterns
- Use `pandas` for Excel/CSV operations (already in requirements)
- Read with `pd.read_excel()` or `pd.read_csv()`, write with `df.to_excel()` or `df.to_csv()`
- Always specify `encoding='utf-8'` for text files
- Use `openpyxl` engine for Excel files (already in requirements)

## Testing

### Test Structure
Tests use Python's built-in `unittest` framework:
- Test files: `tests/test_*.py`
- Mirror the structure of `src/` modules
- Use temporary directories for filesystem tests
- Mock external HTTP calls to avoid network dependencies

### Test Coverage Priorities
Focus testing on:
- Config parsing and validation (`test_config.py`)
- I/O helpers and file operations (`test_io_helper.py`)
- Recommendation scoring logic (normalization, weighting)
- Progress tracking and resume functionality

## Configuration Reference

### Key Config Sections

**Paths:**
- `output_dir`: Where all Excel/CSV results are saved (default: `output`)
- `logs_dir`: Hidden logs directory (default: `.fs/logs`)
- `progress_dir`: Progress tracking files (default: `.fs/progress`)
- `data_dir`: User-editable fund lists (default: `data`)
- `default_fund_list`: Default input file (default: `data/fund_list.csv`)

**HTTP Settings:**
- `request_delay`: Delay between requests in seconds (default: 0.5)
- `request_timeout`: Request timeout in seconds (default: 30)
- `user_agent`: Browser user agent string for requests

**Batch Processing:**
- `batch_size`: Funds processed per batch (default: 10)
- `save_interval`: Save progress every N records (default: 100)

**Recommendation Weights (Basic Mode):**
```yaml
recommendation_weights:
  recent: 0.35      # Recent momentum
  mid: 0.20         # Mid-term trend
  long: 0.15        # Long-term stability
  risk_penalty: 0.10  # Volatility penalty
  manager: 0.10     # Manager performance
  scale: 0.05       # Fund size
  rating: 0.30      # Agency ratings
  age: 0.02         # Fund age
```

Override via environment variables: `FUNDSEEKER_RECENT_WEIGHT`, `FUNDSEEKER_MID_WEIGHT`, etc.

**Advanced Model Configuration:**
```yaml
advanced_model:
  - label: 6m              # Variant identifier
    db_path: ../fund_reco_fit/data/fundseeker_nav.db
    feature_table: features_M_star
    weights_path: ../fund_reco_fit/models/model_params_6m.json
    top_k: 200
```

Multiple variants can be configured; use `--adv-variant <label>` to select.

## Common Workflows

### Adding a New Service
1. Create `src/services/new_service.py` with a class that accepts `AppConfig`
2. Implement the main logic in a `run()` method
3. Add command to `.main.py` using `@app.command()` decorator
4. Wire the service in the menu actions dict if needed
5. Update shell scripts if the command should be easily accessible

### Adding a New Fetcher
1. Create `src/data/new_fetcher.py` with functions for HTTP requests and parsing
2. Use `requests` library with configured timeout and user agent
3. Add appropriate delays between requests using `time.sleep(cfg.request_delay)`
4. Return structured data (dict or list) for service layer to process
5. Handle HTTP errors gracefully and return None or raise custom exceptions

### Modifying Recommendation Weights
1. Edit `config.yaml` under `recommendation_weights` section
2. Or set environment variables: `export FUNDSEEKER_RECENT_WEIGHT=0.4`
3. Re-run `./fundseeker.sh recommend` to generate new recommendations
4. Compare outputs by checking different timestamped files in `output/`

### Debugging Failed Fetches
1. Check logs in `.fs/logs/<date>/` for error messages
2. Verify network connectivity and Eastmoney website availability
3. Check if rate limiting is occurring (increase `request_delay` in config)
4. Use progress files in `.fs/progress/` to identify which funds failed
5. Re-run with `--no-resume` to start fresh if progress is corrupted

## Important Notes

### Data Sources
All data is fetched from Eastmoney (fund.eastmoney.com):
- Rankings API: `http://fund.eastmoney.com/data/rankhandler.aspx`
- Fund details: `http://fundf10.eastmoney.com/`
- NAV data: `http://fund.eastmoney.com/f10/F10DataApi.aspx`

### File Organization
- **Never commit** `output/` or `.fs/` directories (ephemeral data)
- **Never commit** personal fund lists in `data/fund_list.csv`
- Keep `templates/` for reference templates only
- Archive old outputs manually if needed; system doesn't auto-clean

### Dependencies
Core dependencies (see `requirements.txt`):
- `typer`: CLI framework with type hints
- `pandas`: Data manipulation and Excel/CSV I/O
- `requests`: HTTP client for data fetching
- `openpyxl`: Excel file format support
- `PyYAML`: Configuration file parsing
- `numpy`: Numerical operations for scoring

### Sister Project Integration
The `fund_reco_fit/` directory contains advanced feature engineering:
- Imports NAV data into SQLite (`fundseeker_nav.db`)
- Computes 36-month rolling metrics (returns, volatility, drawdowns)
- Trains factor models with cross-validation
- Exports model weights as JSON for `AdvancedRecommendService`

To use advanced recommendations, first run the feature pipeline in `fund_reco_fit/`, then configure `advanced_model` in `config.yaml`.

### Commit Conventions
Follow the existing commit style:
- Use concise, action-focused subjects (English or Chinese)
- Keep subject line under 72 characters
- Examples: "Update recommendation system: increase top_n option to 200", "增加windows适配"
- Describe the "why" in the commit body for non-trivial changes

## Documentation

Key documentation files:
- `README.md`: User-facing quick start guide
- `PROJECT_OVERVIEW.md`: Project goals and data workflow
- `doc/requirements.md`: Detailed requirements specification
- `doc/design.md`: Architecture and design decisions
- `doc/user_manual.md`: Comprehensive user manual
- `doc/recommendation_business_design.md`: Recommendation system design
- `doc/test_cases.md`: Test scenarios and validation

## Troubleshooting

**Issue: "未找到基金列表文件"**
- Ensure `data/fund_list.csv` exists and contains fund codes
- Copy from `templates/fund_list_template.csv` if needed

**Issue: Progress not resuming**
- Check `.fs/progress/` for valid JSON files
- Use `--no-resume` to start fresh if corrupted

**Issue: Rate limiting / HTTP errors**
- Increase `request_delay` in `config.yaml` (try 1.0 or 2.0 seconds)
- Check Eastmoney website availability

**Issue: Advanced mode not working**
- Verify `fund_reco_fit/data/fundseeker_nav.db` exists
- Check model weights path in `config.yaml`
- Ensure SQLite database has required feature tables
