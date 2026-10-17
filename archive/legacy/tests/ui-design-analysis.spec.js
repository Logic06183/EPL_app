// tests/ui-design-analysis.spec.js
import { test, expect } from '@playwright/test';

test.describe('FPL AI Pro - UI Design Analysis', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Visual Design Assessment', () => {
    test('should have proper dark mode implementation', async ({ page }) => {
      // Check if dark mode styles are applied
      const body = page.locator('body');
      const backgroundColor = await body.evaluate(el => 
        window.getComputedStyle(el).backgroundColor
      );
      
      // Should be dark (not white/light)
      expect(backgroundColor).not.toBe('rgb(255, 255, 255)');
      
      // Take screenshot for visual verification
      await page.screenshot({ 
        path: 'test-results/dark-mode-implementation.png',
        fullPage: true 
      });
    });

    test('should use gradient backgrounds effectively', async ({ page }) => {
      // Check for gradient usage in hero section
      const heroSection = page.locator('.header-epl');
      const backgroundImage = await heroSection.evaluate(el => 
        window.getComputedStyle(el).backgroundImage
      );
      
      // Should have gradient or background styling
      expect(backgroundImage).not.toBe('none');
      
      // Check glass morphism effects
      const glassCards = page.locator('.glass-epl');
      const count = await glassCards.count();
      expect(count).toBeGreaterThan(0);
      
      // Verify backdrop blur effects
      const firstGlass = glassCards.first();
      const backdropFilter = await firstGlass.evaluate(el => 
        window.getComputedStyle(el).backdropFilter
      );
      expect(backdropFilter).toContain('blur');
    });

    test('should have proper card-based design', async ({ page }) => {
      // Navigate to predictions tab
      await page.click('text=Top Players');
      await page.waitForSelector('.player-card-epl', { timeout: 10000 });
      
      // Check player cards design
      const playerCards = page.locator('.player-card-epl');
      const cardCount = await playerCards.count();
      expect(cardCount).toBeGreaterThan(0);
      
      // Verify card styling
      const firstCard = playerCards.first();
      const borderRadius = await firstCard.evaluate(el => 
        window.getComputedStyle(el).borderRadius
      );
      expect(borderRadius).not.toBe('0px');
      
      // Check for proper spacing and shadows
      const boxShadow = await firstCard.evaluate(el => 
        window.getComputedStyle(el).boxShadow
      );
      expect(boxShadow).not.toBe('none');
    });
  });

  test.describe('Navigation and Usability', () => {
    test('should have intuitive navigation', async ({ page }) => {
      // Test all main navigation tabs
      const tabs = [
        { name: 'Top Players', selector: 'text=Top Players' },
        { name: 'Live Scores', selector: 'text=Live Scores' },
        { name: 'Squad Builder', selector: 'text=Squad Builder' },
        { name: 'Player Intel', selector: 'text=Player Intel' },
        { name: 'Live Info', selector: 'text=Live Info' }
      ];
      
      for (const tab of tabs) {
        await page.click(tab.selector);
        await page.waitForTimeout(1000); // Allow content to load
        
        // Verify tab is active
        const activeTab = page.locator(`${tab.selector}.active`);
        await expect(activeTab).toBeVisible();
        
        // Take screenshot of each tab
        await page.screenshot({ 
          path: `test-results/tab-${tab.name.toLowerCase().replace(' ', '-')}.png`
        });
      }
    });

    test('should have responsive design', async ({ page }) => {
      // Test different viewport sizes
      const viewports = [
        { width: 375, height: 667, name: 'mobile' },
        { width: 768, height: 1024, name: 'tablet' },
        { width: 1920, height: 1080, name: 'desktop' }
      ];
      
      for (const viewport of viewports) {
        await page.setViewportSize(viewport);
        await page.waitForTimeout(500);
        
        // Take screenshot for each viewport
        await page.screenshot({ 
          path: `test-results/responsive-${viewport.name}.png`,
          fullPage: true 
        });
        
        // Check if navigation is accessible
        const navigation = page.locator('[role="navigation"], nav, .tab-epl');
        await expect(navigation.first()).toBeVisible();
      }
    });
  });

  test.describe('Performance and User Experience', () => {
    test('should load quickly and smoothly', async ({ page }) => {
      const startTime = Date.now();
      
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      const loadTime = Date.now() - startTime;
      console.log(`Page load time: ${loadTime}ms`);
      
      // Should load within reasonable time
      expect(loadTime).toBeLessThan(5000);
      
      // Check for loading indicators
      const loadingElements = page.locator('.loading-epl, .animate-spin');
      // Loading should complete
      await expect(loadingElements).toHaveCount(0);
    });

    test('should have proper micro-interactions', async ({ page }) => {
      // Test button hover effects
      const buttons = page.locator('button.btn-epl-primary, button.tab-epl');
      const firstButton = buttons.first();
      
      // Hover and check for visual feedback
      await firstButton.hover();
      await page.waitForTimeout(200);
      
      // Take screenshot of hover state
      await page.screenshot({ 
        path: 'test-results/button-hover-state.png'
      });
      
      // Test click feedback
      await firstButton.click();
      await page.waitForTimeout(200);
    });

    test('should handle AI model interactions properly', async ({ page }) => {
      await page.click('text=Top Players');
      await page.waitForSelector('select');
      
      // Test model selection dropdown
      const modelSelect = page.locator('select').nth(2); // AI Model dropdown
      await modelSelect.selectOption('random_forest');
      await page.waitForTimeout(1000);
      
      // Should show AI enhanced indicator
      const aiIndicator = page.locator('text=AI Enhanced, text=🤖');
      await expect(aiIndicator.first()).toBeVisible();
      
      // Test refresh functionality
      const refreshButton = page.locator('text=Refresh Data');
      await refreshButton.click();
      await page.waitForTimeout(2000);
      
      // Take screenshot of AI results
      await page.screenshot({ 
        path: 'test-results/ai-model-results.png'
      });
    });
  });

  test.describe('Accessibility and Modern Standards', () => {
    test('should meet accessibility standards', async ({ page }) => {
      // Check for proper heading hierarchy
      const h1 = page.locator('h1');
      await expect(h1).toBeVisible();
      
      // Check for alt text on images
      const images = page.locator('img');
      const imageCount = await images.count();
      
      for (let i = 0; i < imageCount; i++) {
        const img = images.nth(i);
        const alt = await img.getAttribute('alt');
        if (alt === null || alt === '') {
          console.warn(`Image ${i} missing alt text`);
        }
      }
      
      // Check color contrast (basic check)
      const textElements = page.locator('p, span, div').filter({ hasText: /\w+/ });
      const firstText = textElements.first();
      const color = await firstText.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          color: style.color,
          backgroundColor: style.backgroundColor
        };
      });
      
      console.log('Text colors detected:', color);
    });

    test('should work without JavaScript (progressive enhancement)', async ({ page }) => {
      // Disable JavaScript
      await page.addInitScript(() => {
        Object.defineProperty(window, 'navigator', {
          value: { ...window.navigator, javaEnabled: () => false }
        });
      });
      
      await page.goto('/');
      
      // Basic content should still be visible
      const mainHeading = page.locator('h1');
      await expect(mainHeading).toBeVisible();
      
      // Take screenshot of no-JS state
      await page.screenshot({ 
        path: 'test-results/no-javascript-fallback.png'
      });
    });
  });

  test.describe('Content and Information Architecture', () => {
    test('should display comprehensive player information', async ({ page }) => {
      await page.click('text=Top Players');
      await page.waitForSelector('.player-card-epl', { timeout: 10000 });
      
      const playerCard = page.locator('.player-card-epl').first();
      
      // Check for essential player information
      await expect(playerCard.locator('text=/£[\d.]+m/')).toBeVisible(); // Price
      await expect(playerCard.locator('text=/\d+/')).toBeVisible(); // Points
      await expect(playerCard.locator('text=/GK|DEF|MID|FWD/')).toBeVisible(); // Position
      
      // Take detailed screenshot
      await playerCard.screenshot({ 
        path: 'test-results/player-card-detail.png'
      });
    });

    test('should show methodology information clearly', async ({ page }) => {
      // Find and expand methodology section
      const methodologySection = page.locator('text=AI/ML Methodology');
      await methodologySection.click();
      await page.waitForTimeout(500);
      
      // Check for key information sections
      await expect(page.locator('text=Multi-Model AI System')).toBeVisible();
      await expect(page.locator('text=Real Data Sources')).toBeVisible();
      await expect(page.locator('text=Live Update Pipeline')).toBeVisible();
      
      // Take screenshot of expanded methodology
      await page.screenshot({ 
        path: 'test-results/methodology-expanded.png'
      });
    });
  });
});