# Archive Directory

This directory contains old code files from before the refactoring (February 2026).

## What's Archived

### `/old_api_files/`
Old API implementations that have been consolidated into `backend/app/main.py`:
- `api_production.py` - Original production API
- `enhanced_api_production.py` - Enhanced version with xG/xA
- `api_ai_enhanced.py` - AI-enhanced version
- `api_with_ai.py` - Alternative AI version
- `api_enhanced_final.py` - Another variant
- `api_lightweight.py` - Lightweight version

### `/old_scripts/`
Utility scripts and one-off files:
- Various helper scripts
- Local demo files
- Testing scripts

### `/old_models/`
Old ML model implementations:
- Legacy model training scripts
- Old prediction engines

### `/old_integrations/`
Integration modules that have been refactored:
- PayStack integration
- SportMonks integration
- News sentiment analyzer
- Gemini integration

## New Structure

All functionality has been reorganized into:

```
backend/
├── app/
│   ├── main.py              # Consolidated API
│   ├── api/                 # API routes
│   ├── services/            # Business logic
│   ├── models/              # ML models
│   └── utils/               # Utilities
```

## Why Archived?

These files are kept for reference but are no longer used:
- ✅ Consolidated into new backend structure
- ✅ Duplicate code removed
- ✅ Better organization
- ✅ Modern Python practices

## Restoration

If you need to reference old code:
1. Check this archive
2. Compare with new implementation in `backend/`
3. The new code includes all features from old versions

## Deletion

These files can be safely deleted after:
1. ✅ New backend is tested and working
2. ✅ All features are verified
3. ✅ Production deployment successful
4. ⏱️  30 days retention period

**Created:** February 15, 2026
**Status:** Safe to delete after successful deployment
