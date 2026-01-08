# A/B Testing Guide

## Overview

This guide describes how to set up and execute A/B testing for Gumtree messenger automation.

## Prerequisites

- Input JSON file with listings (e.g., `bxb_dallas.json` or `claim_links_messenger.json`)
- Python 3.x
- Required dependencies installed

## Setup

### 1. Prepare Input Data

If using raw listings, create ghost listings first:

```bash
python3 create_ghost_listings.py bxb_dallas.json
```

Generate claim links:

```bash
python3 send_claim_links_via_gumtree.py
```

### 2. Configure A/B Test

Run the A/B testing script to split listings into two groups:

```bash
python3 ab_testing.py claim_links_messenger.json \
  --group-a-browser chromium \
  --group-b-browser firefox \
  --group-a-delay 5 \
  --group-b-delay 10
```

The script creates:

- `config_group_a.json` - Configuration for group A
- `config_group_a_listings.json` - Listings for group A
- `config_group_b.json` - Configuration for group B
- `config_group_b_listings.json` - Listings for group B

## Execution

### Group A

1. Update browser in `gumtree_scraper/spiders/gumtree_messenger.py`:

   ```python
   BROWSER = "chromium"
   ```

2. Copy configuration:

   ```bash
   cp config_group_a.json config.json
   ```

3. Run spider:
   ```bash
   scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright
   ```

### Group B

1. Update browser in `gumtree_scraper/spiders/gumtree_messenger.py`:

   ```python
   BROWSER = "firefox"
   ```

2. Copy configuration:

   ```bash
   cp config_group_b.json config.json
   ```

3. Run spider:
   ```bash
   scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright
   ```

## Extract Results

Extract claim URLs after processing:

```bash
python3 extract_claim_urls.py claim_links_messenger.json --limit 100
```

Output file: `claim_urls.txt`

## Configuration Parameters

### Browser Options

- `chromium` - Chrome-based browser
- `firefox` - Firefox browser

### Split Ratios

- `50-50` - Equal distribution (default)
- `70-30` - 70% group A, 30% group B
- `30-70` - 30% group A, 70% group B

### Other Parameters

- `--group-a-delay` / `--group-b-delay` - Message delay in seconds
- `--group-a-template` / `--group-b-template` - Message template file
- `--group-a-max` / `--group-b-max` - Maximum messages to send (0 = all)
- `--group-a-fast` / `--group-b-fast` - Enable fast mode

## Complete Workflow

```bash
# 1. Create ghost listings
python3 create_ghost_listings.py bxb_dallas.json

# 2. Generate claim links
python3 send_claim_links_via_gumtree.py

# 3. Setup A/B test
python3 ab_testing.py claim_links_messenger.json \
  --group-a-browser chromium \
  --group-b-browser firefox \
  --group-a-delay 5 \
  --group-b-delay 10

# 4. Execute group A
cp config_group_a.json config.json
# Update BROWSER in gumtree_messenger.py to "chromium"
scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright

# 5. Execute group B
cp config_group_b.json config.json
# Update BROWSER in gumtree_messenger.py to "firefox"
scrapy crawl gumtree_messenger -s SETTINGS_MODULE=gumtree_scraper.settings_playwright

# 6. Extract results
python3 extract_claim_urls.py claim_links_messenger.json --limit 100
```
