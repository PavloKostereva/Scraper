#!/bin/bash
# Скрипт для запуску масової розсилки claim links через Gumtree

echo "============================================================"
echo "GUMTREE MESSAGING - CLAIM LINKS"
echo "============================================================"
echo ""

# Перевірка config.json
if [ ! -f "config.json" ]; then
    echo "ERROR: config.json not found!"
    echo "Please create config.json with your Gumtree credentials"
    exit 1
fi

# Перевірка claim_message_template.txt
if [ ! -f "claim_message_template.txt" ]; then
    echo "WARNING: claim_message_template.txt not found!"
    echo "Please create claim_message_template.txt with your message template"
    exit 1
fi

# Перевірка claim_links_messenger.json
if [ ! -f "claim_links_messenger.json" ]; then
    echo "WARNING: claim_links_messenger.json not found!"
    echo "Creating it from Supabase..."
    echo ""
    python3 send_claim_links_via_gumtree.py
    echo ""
    
    if [ ! -f "claim_links_messenger.json" ]; then
        echo "ERROR: Failed to create claim_links_messenger.json"
        echo "Please run manually: python3 send_claim_links_via_gumtree.py"
        exit 1
    fi
fi

echo "All files ready"
echo ""
echo "Starting messenger..."
echo ""

# Запуск messenger
python3 -m scrapy crawl gumtree_messenger \
  -s SETTINGS_MODULE=gumtree_scraper.settings_playwright \
  -s PLAYWRIGHT_LAUNCH_OPTIONS='{"headless": false}'

echo ""
echo "============================================================"
echo "Messaging completed!"
echo "Check contacted_listings.json for results"
echo "============================================================"

