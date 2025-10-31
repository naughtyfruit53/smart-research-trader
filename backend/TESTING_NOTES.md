# Testing Notes for Feature Engineering Pipeline

## Status

✅ **Implemented and Tested (without ta library)**:
- `fundamentals.py`: As-of join and relative valuation - TESTED ✓
- `sentiment.py`: News sentiment aggregation - TESTED ✓
- `joiner.py`: Feature joining - TESTED ✓
- `composite.py`: Composite scores - TESTED ✓
- `config.py`: Configuration helpers - TESTED ✓

⏳ **Pending ta Library Installation**:
- `technicals.py`: Technical indicators (requires `ta==0.11.0`)
- Full integration tests
- CI pipeline validation

## Manual Testing Performed

### Fundamentals Module
```python
# Test as-of join
result = asof_join_fundamentals(trading_days, fundamentals)
# ✓ Shape: (5, 4)
# ✓ PE values correctly joined
# ✓ Forward-fill works

# Test relative valuation
result = relative_valuation(df, sector_mapping=None)
# ✓ pe_vs_sector and pb_vs_sector columns created
# ✓ Cross-sectional z-scores computed correctly
```

### Sentiment Module
```python
result = aggregate_news_sentiment(news, trading_days)
# ✓ Shape: (5, 6)
# ✓ Columns: sent_mean_comp, burst_3d, burst_7d, sent_ma_7d
# ✓ Day 1 sentiment mean: 0.6 (correct average of 0.5 and 0.7)
```

### Joiner Module
```python
result = join_features(technicals, fundamentals, sentiment)
# ✓ Joined result shape: (3, 15)
# ✓ All columns present
```

### Composite Module
```python
result = compute_composite_scores(df)
# ✓ composite_score column exists
# ✓ quality_score, valuation_score, momentum_score, sentiment_score all created
# ✓ Sample composite score: 1.0 (expected for single ticker on first date)
```

## Once ta Library is Available

### Installation
```bash
pip install ta==0.11.0 scikit-learn==1.4.0
```

### Run Full Test Suite
```bash
cd backend
pytest tests/test_features_technicals_shapes.py -v
pytest tests/test_features_fundamentals_asof.py -v
pytest tests/test_features_sentiment_aggregates.py -v
pytest tests/test_features_joiner_no_leakage.py -v
pytest tests/test_compute_features_upsert_idempotent.py -v
```

### Run Integration Test
```bash
# Ensure database is running and populated with sample data
python -m src.data.etl.compute_features --tickers AAPL,MSFT --start-date 2024-01-01 --end-date 2024-01-31

# Or use convenience script
./run_compute_features.sh --tickers AAPL,MSFT --start-date 2024-01-01 --end-date 2024-01-31
```

### Expected Behavior

1. **Technical Indicators**: Should compute all 19 indicators without errors
   - First 20 rows may have NaN for SMA_20 (warmup)
   - First 200 rows may have NaN for SMA_200 (warmup)
   
2. **Fundamentals**: Should join correctly with forward-fill up to 120 days

3. **Sentiment**: Should aggregate news and compute burst metrics

4. **Composite Scores**: Should produce values in [0, 1] range for all sub-scores

5. **Database**: 
   - Features table should have rows with primary key (ticker, dt)
   - features_json should contain all computed features
   - Re-running should be idempotent (no duplicates)

### Validation Queries

```sql
-- Check feature count
SELECT ticker, COUNT(*) 
FROM features 
GROUP BY ticker;

-- Check sample features
SELECT ticker, dt, features_json->'composite_score' as composite_score
FROM features
ORDER BY ticker, dt
LIMIT 10;

-- Check for NULLs in composite_score
SELECT COUNT(*) 
FROM features 
WHERE (features_json->>'composite_score')::float IS NULL;
```

## CI Pipeline Expectations

When CI runs with ta library installed:

1. All 5 test files should pass
2. No import errors
3. Tests should complete in < 5 minutes
4. Code should pass ruff, black, mypy checks

## Known Limitations

1. **Network Issues**: pip installation of `ta` library timed out during development
   - This is a temporary infrastructure issue
   - CI environment should have better connectivity

2. **ta Library**: Uses pandas and numpy, may take time to install
   - Consider pre-building Docker images with ta installed
   - Or use poetry/pipenv for better dependency management

3. **Database Required**: Tests use actual PostgreSQL (not mocked)
   - This is by design for integration testing
   - Fixture data is small and created programmatically

## Troubleshooting

### Import Error: No module named 'ta'
```bash
pip install ta==0.11.0
```

### Import Error: No module named 'sklearn'
```bash
pip install scikit-learn==1.4.0
```

### Database Connection Error
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test connection
python -c "from src.db.session import check_db_health; print(check_db_health())"
```

### Tests Fail with "Insufficient Data"
- Ensure prices table has at least 200+ days of data per ticker
- Technical indicators need warmup period

### Composite Score is NaN
- Check that all sub-scores are being computed
- Check that input features have sufficient non-null values
- Review logs for warnings about missing metrics
