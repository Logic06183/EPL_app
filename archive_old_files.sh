#!/bin/bash
# Archive old Python files after refactoring
# Created: 2026-02-15

echo "🗄️  Archiving old Python files..."

# Archive old API files
echo "Moving API files..."
mv api_production.py archive/old_api_files/ 2>/dev/null
mv enhanced_api_production.py archive/old_api_files/ 2>/dev/null
mv api_ai_enhanced.py archive/old_api_files/ 2>/dev/null
mv api_with_ai.py archive/old_api_files/ 2>/dev/null
mv api_enhanced_final.py archive/old_api_files/ 2>/dev/null
mv api_lightweight.py archive/old_api_files/ 2>/dev/null
mv simple_api.py archive/old_api_files/ 2>/dev/null

# Archive integration files
echo "Moving integration files..."
mv paystack_integration.py archive/old_integrations/ 2>/dev/null
mv sportmonks_integration.py archive/old_integrations/ 2>/dev/null
mv news_sentiment_analyzer.py archive/old_integrations/ 2>/dev/null
mv gemini_integration.py archive/old_integrations/ 2>/dev/null

# Archive ML/model files
echo "Moving model files..."
mv hybrid_forecaster_enhanced.py archive/old_models/ 2>/dev/null
mv multi_model_predictor.py archive/old_models/ 2>/dev/null
mv train_pytorch_model.py archive/old_models/ 2>/dev/null

# Archive utility files
echo "Moving utility files..."
mv performance_utils.py archive/old_scripts/ 2>/dev/null
mv security_utils.py archive/old_scripts/ 2>/dev/null
mv prediction_scheduler.py archive/old_scripts/ 2>/dev/null

# Archive scripts and demos
echo "Moving scripts..."
mv local_demo.py archive/old_scripts/ 2>/dev/null
mv run.py archive/old_scripts/ 2>/dev/null
mv run_tests.py archive/old_scripts/ 2>/dev/null
mv cli.py archive/old_scripts/ 2>/dev/null
mv start_local.py archive/old_scripts/ 2>/dev/null

# Archive main.py (replaced by backend/app/main.py)
mv main.py archive/old_api_files/main_old.py 2>/dev/null

# Archive requirements files
echo "Moving old requirements files..."
mv requirements_*.txt archive/old_requirements/ 2>/dev/null

echo "✅ Archiving complete!"
echo ""
echo "Archived files are in:"
echo "  - archive/old_api_files/"
echo "  - archive/old_integrations/"
echo "  - archive/old_models/"
echo "  - archive/old_scripts/"
echo "  - archive/old_requirements/"
echo ""
echo "New structure is in:"
echo "  - backend/app/"
