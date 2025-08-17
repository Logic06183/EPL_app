const { test, expect } = require('@playwright/test');

test.describe('EPL Production Website Tests', () => {
  let consoleErrors = [];
  let networkRequests = [];
  let apiErrors = [];

  test.beforeEach(async ({ page }) => {
    // Reset arrays for each test
    consoleErrors = [];
    networkRequests = [];
    apiErrors = [];

    // Listen to console messages
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push({
          type: msg.type(),
          text: msg.text(),
          location: msg.location()
        });
      }
    });

    // Listen to network requests
    page.on('request', request => {
      networkRequests.push({
        url: request.url(),
        method: request.method(),
        headers: request.headers()
      });
    });

    // Listen to network responses
    page.on('response', response => {
      if (!response.ok()) {
        apiErrors.push({
          url: response.url(),
          status: response.status(),
          statusText: response.statusText()
        });
      }
    });
  });

  test('Navigate to production site and take screenshot', async ({ page }) => {
    console.log('🌐 Navigating to production site...');
    
    await page.goto('https://epl-prediction-app.web.app', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });

    // Take initial screenshot
    await page.screenshot({ 
      path: 'screenshots/homepage.png', 
      fullPage: true 
    });

    // Check if page loaded successfully
    const title = await page.title();
    console.log(`📋 Page title: ${title}`);

    // Log any console errors from initial load
    if (consoleErrors.length > 0) {
      console.log('❌ Console errors during initial load:');
      consoleErrors.forEach(error => {
        console.log(`  - ${error.text} (${error.location?.url}:${error.location?.lineNumber})`);
      });
    } else {
      console.log('✅ No console errors during initial load');
    }
  });

  test('Test AI Forecaster tab functionality', async ({ page }) => {
    console.log('🤖 Testing AI Forecaster tab...');
    
    await page.goto('https://epl-prediction-app.web.app', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });

    // Look for AI Forecaster tab/button
    const aiForecasterButton = page.locator('text="AI Forecaster"').or(
      page.locator('[data-testid*="forecaster"]')
    ).or(
      page.locator('button:has-text("Forecaster")')
    ).or(
      page.locator('tab:has-text("AI")')
    ).first();

    if (await aiForecasterButton.count() > 0) {
      console.log('✅ AI Forecaster tab found');
      
      // Click on AI Forecaster
      await aiForecasterButton.click();
      await page.waitForTimeout(3000); // Wait for content to load

      // Take screenshot of AI Forecaster
      await page.screenshot({ 
        path: 'screenshots/ai-forecaster.png', 
        fullPage: true 
      });

      // Check for prediction content
      const predictionContent = await page.locator('text=/prediction|forecast|match|team/i').count();
      console.log(`📊 Found ${predictionContent} prediction-related elements`);

      // Check for loading states
      const loadingElements = await page.locator('text=/loading|spinner|wait/i').count();
      if (loadingElements > 0) {
        console.log('⏳ Loading elements found - waiting for content...');
        await page.waitForTimeout(5000);
      }

    } else {
      console.log('❌ AI Forecaster tab not found');
      
      // Try to find any tabs or navigation
      const allButtons = await page.locator('button').allTextContents();
      const allLinks = await page.locator('a').allTextContents();
      console.log('Available buttons:', allButtons.slice(0, 10));
      console.log('Available links:', allLinks.slice(0, 10));
    }

    // Log console errors specific to AI Forecaster
    const forecasterErrors = consoleErrors.filter(error => 
      error.text.toLowerCase().includes('forecast') || 
      error.text.toLowerCase().includes('prediction') ||
      error.text.toLowerCase().includes('gemini') ||
      error.text.toLowerCase().includes('ai')
    );
    
    if (forecasterErrors.length > 0) {
      console.log('❌ AI Forecaster related errors:');
      forecasterErrors.forEach(error => {
        console.log(`  - ${error.text}`);
      });
    }
  });

  test('Check backend API connectivity', async ({ page }) => {
    console.log('🔌 Testing backend API connectivity...');
    
    await page.goto('https://epl-prediction-app.web.app', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });

    // Wait for potential API calls
    await page.waitForTimeout(5000);

    // Filter requests to backend API
    const backendRequests = networkRequests.filter(req => 
      req.url.includes('epl-backend-77913915885.us-central1.run.app')
    );

    console.log(`📡 Found ${backendRequests.length} requests to backend API:`);
    backendRequests.forEach(req => {
      console.log(`  - ${req.method} ${req.url}`);
    });

    // Check for CORS headers in requests
    const corsRequests = backendRequests.filter(req => 
      req.headers['access-control-allow-origin'] || 
      req.headers['origin']
    );
    
    if (corsRequests.length > 0) {
      console.log('🔄 CORS related requests found');
    }

    // Test health endpoint directly
    try {
      const response = await page.request.get('https://epl-backend-77913915885.us-central1.run.app/health');
      console.log(`🏥 Health endpoint status: ${response.status()}`);
      if (response.ok()) {
        const healthData = await response.json();
        console.log('✅ Health endpoint response:', healthData);
      }
    } catch (error) {
      console.log('❌ Health endpoint error:', error.message);
    }

    // Test predictions endpoint
    try {
      const response = await page.request.get('https://epl-backend-77913915885.us-central1.run.app/api/predictions');
      console.log(`🔮 Predictions endpoint status: ${response.status()}`);
      if (response.ok()) {
        const predictions = await response.json();
        console.log(`✅ Predictions endpoint returned ${predictions.length || 'unknown'} items`);
      }
    } catch (error) {
      console.log('❌ Predictions endpoint error:', error.message);
    }
  });

  test('Test navigation between tabs', async ({ page }) => {
    console.log('🧭 Testing navigation between tabs...');
    
    await page.goto('https://epl-prediction-app.web.app', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });

    const tabsToTest = [
      'Top Players',
      'Live Scores', 
      'Squad Builder',
      'Predictions',
      'Fixtures',
      'Table',
      'Stats'
    ];

    for (const tabName of tabsToTest) {
      console.log(`🔍 Looking for ${tabName} tab...`);
      
      const tabElement = page.locator(`text="${tabName}"`).or(
        page.locator(`[data-testid*="${tabName.toLowerCase().replace(' ', '-')}"]`)
      ).or(
        page.locator(`button:has-text("${tabName}")`)
      ).or(
        page.locator(`a:has-text("${tabName}")`)
      ).first();

      if (await tabElement.count() > 0) {
        console.log(`✅ Found ${tabName} tab`);
        
        try {
          await tabElement.click();
          await page.waitForTimeout(2000);
          
          // Take screenshot
          await page.screenshot({ 
            path: `screenshots/${tabName.toLowerCase().replace(' ', '-')}.png`,
            fullPage: true 
          });
          
          console.log(`📸 Screenshot taken for ${tabName}`);
        } catch (error) {
          console.log(`❌ Error clicking ${tabName}: ${error.message}`);
        }
      } else {
        console.log(`❌ ${tabName} tab not found`);
      }
    }
  });

  test('Analyze API errors and CORS issues', async ({ page }) => {
    console.log('🔍 Analyzing API errors and CORS issues...');
    
    await page.goto('https://epl-prediction-app.web.app', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });

    // Wait for all potential API calls
    await page.waitForTimeout(10000);

    // Log all API errors
    if (apiErrors.length > 0) {
      console.log('❌ API Errors found:');
      apiErrors.forEach(error => {
        console.log(`  - ${error.status} ${error.statusText}: ${error.url}`);
      });
    } else {
      console.log('✅ No API errors detected');
    }

    // Check for CORS specific errors in console
    const corsErrors = consoleErrors.filter(error => 
      error.text.toLowerCase().includes('cors') ||
      error.text.toLowerCase().includes('cross-origin') ||
      error.text.toLowerCase().includes('access-control-allow-origin')
    );

    if (corsErrors.length > 0) {
      console.log('❌ CORS related errors:');
      corsErrors.forEach(error => {
        console.log(`  - ${error.text}`);
      });
    } else {
      console.log('✅ No CORS errors detected');
    }

    // Log all console errors
    if (consoleErrors.length > 0) {
      console.log('❌ All console errors:');
      consoleErrors.forEach(error => {
        console.log(`  - ${error.text} (${error.location?.url}:${error.location?.lineNumber})`);
      });
    }

    // Summary of network requests
    const totalRequests = networkRequests.length;
    const backendRequests = networkRequests.filter(req => 
      req.url.includes('epl-backend-77913915885.us-central1.run.app')
    ).length;
    const failedRequests = apiErrors.length;

    console.log(`📊 Network Summary:`);
    console.log(`  - Total requests: ${totalRequests}`);
    console.log(`  - Backend API requests: ${backendRequests}`);
    console.log(`  - Failed requests: ${failedRequests}`);
  });
});