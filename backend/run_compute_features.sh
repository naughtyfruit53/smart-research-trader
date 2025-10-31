#!/bin/bash
# Script to run feature computation

set -e

cd "$(dirname "$0")"

# Check if ta library is installed
python -c "import ta" 2>/dev/null || {
    echo "ERROR: ta library not installed"
    echo "Install with: pip install ta==0.11.0"
    exit 1
}

# Check if scikit-learn is installed
python -c "import sklearn" 2>/dev/null || {
    echo "ERROR: scikit-learn not installed"
    echo "Install with: pip install scikit-learn==1.4.0"
    exit 1
}

# Check database connection
python -c "from src.db.session import check_db_health; assert check_db_health(), 'Database not healthy'" || {
    echo "ERROR: Cannot connect to database"
    echo "Check DATABASE_URL environment variable"
    exit 1
}

# Run compute_features with provided arguments or defaults
echo "Running feature computation..."
python -m src.data.etl.compute_features "$@"

echo "Feature computation complete!"
