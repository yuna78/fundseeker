#!/bin/bash
# Quick validation script for fund selection models

echo "🚀 Fund Model Validation System"
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if database exists
if [ ! -f "data/fundseeker_nav.db" ]; then
    echo "❌ Database not found at data/fundseeker_nav.db"
    echo "   Please run nav_importer and feature_builder first."
    exit 1
fi

echo "Select validation mode:"
echo "1) Walk-Forward Validation (test model stability over time)"
echo "2) 2025 Real Data Validation (compare predictions with actual 2025 results)"
echo "3) Both"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1|3)
        echo ""
        echo "📊 Running Walk-Forward Validation..."
        python -m src.run_validation walk-forward \
            --database data/fundseeker_nav.db \
            --start-date 2020-01-01 \
            --end-date 2025-12-31 \
            --train-months 24 \
            --test-months 6 \
            --step-months 6 \
            --top-k 30 \
            --output-json output/walk_forward_results.json
        ;;
esac

case $choice in
    2|3)
        echo ""
        echo "🎯 Running 2025 Real Data Validation..."
        python -m src.run_validation validate-2025 \
            --database data/fundseeker_nav.db \
            --weights-json models/model_params_6m.json \
            --prediction-dates "2024-06-30,2024-12-31" \
            --horizon-months 6 \
            --top-k 30 \
            --output-json output/validation_2025_results.json
        ;;
esac

echo ""
echo "✅ Validation complete! Check output/ directory for results."
