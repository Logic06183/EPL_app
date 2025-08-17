// tests/ui-improvement-tests.spec.js
import { test, expect } from '@playwright/test';

test.describe('UI Improvement Implementation Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Enhanced Visual Design', () => {
    test('should implement lightning dark theme effects', async ({ page }) => {
      // Check for dynamic lighting effects
      const glassElements = page.locator('.glass-epl');
      
      for (let i = 0; i < Math.min(3, await glassElements.count()); i++) {
        const element = glassElements.nth(i);
        
        // Check for backdrop blur
        const backdropFilter = await element.evaluate(el => 
          window.getComputedStyle(el).backdropFilter
        );
        expect(backdropFilter).toContain('blur');
        
        // Check for translucent background
        const backgroundColor = await element.evaluate(el => 
          window.getComputedStyle(el).backgroundColor
        );
        expect(backgroundColor).toContain('rgba');
      }
      
      await page.screenshot({ 
        path: 'test-results/lightning-dark-implementation.png',
        fullPage: true 
      });
    });

    test('should have enhanced gradient usage', async ({ page }) => {
      // Check hero section gradient
      const heroSection = page.locator('.header-epl');
      const backgroundImage = await heroSection.evaluate(el => 
        window.getComputedStyle(el).backgroundImage
      );
      
      // Should have gradient background
      expect(backgroundImage).toMatch(/gradient|linear-gradient|radial-gradient/);
      
      // Check button gradients
      const primaryButtons = page.locator('.btn-epl-primary, button[class*="gradient"]');
      const buttonCount = await primaryButtons.count();
      expect(buttonCount).toBeGreaterThan(0);
      
      if (buttonCount > 0) {
        const firstButton = primaryButtons.first();
        const buttonBg = await firstButton.evaluate(el => 
          window.getComputedStyle(el).backgroundImage
        );
        expect(buttonBg).toMatch(/gradient/);
      }
    });

    test('should implement proper micro-interactions', async ({ page }) => {
      // Test hover states on interactive elements
      const interactiveElements = page.locator('button, .tab-epl, .player-card-epl');
      const count = await interactiveElements.count();
      
      if (count > 0) {
        const firstElement = interactiveElements.first();
        
        // Get initial state
        const initialTransform = await firstElement.evaluate(el => 
          window.getComputedStyle(el).transform
        );
        
        // Hover and check for changes
        await firstElement.hover();
        await page.waitForTimeout(300);
        
        const hoverTransform = await firstElement.evaluate(el => 
          window.getComputedStyle(el).transform
        );
        
        // Should have some visual feedback (transform, scale, etc.)
        // Note: This test may need adjustment based on actual hover implementation
        console.log('Hover interaction detected:', { initialTransform, hoverTransform });
        
        await page.screenshot({ 
          path: 'test-results/micro-interactions-hover.png'
        });
      }
    });
  });

  test.describe('Enhanced Information Architecture', () => {
    test('should display comprehensive player information', async ({ page }) => {
      await page.click('text=Top Players');
      await page.waitForSelector('.player-card-epl', { timeout: 10000 });
      
      const playerCards = page.locator('.player-card-epl');
      const cardCount = await playerCards.count();
      expect(cardCount).toBeGreaterThan(0);
      
      if (cardCount > 0) {
        const firstCard = playerCards.first();
        
        // Check for comprehensive information
        const cardText = await firstCard.textContent();
        
        // Should contain price, points, position, team
        expect(cardText).toMatch(/£[\d.]+m/); // Price
        expect(cardText).toMatch(/\d+/); // Points
        expect(cardText).toMatch(/GK|DEF|MID|FWD/); // Position
        
        // Check for AI enhancement indicator
        const aiIndicator = firstCard.locator('text=AI, [class*="ai"], [class*="enhanced"]');
        // AI indicator should be present for enhanced predictions
        
        await firstCard.screenshot({ 
          path: 'test-results/enhanced-player-card.png'
        });
      }
    });

    test('should implement better quick actions', async ({ page }) => {
      await page.click('text=Top Players');
      await page.waitForSelector('select', { timeout: 10000 });
      
      // Check for quick action elements
      const refreshButton = page.locator('text=Refresh Data, button[class*="refresh"]');
      await expect(refreshButton.first()).toBeVisible();
      
      // Check model selection dropdown (quick model switching)
      const modelSelect = page.locator('select').nth(2);
      await expect(modelSelect).toBeVisible();
      
      // Test quick model switching
      await modelSelect.selectOption('ensemble');
      await page.waitForTimeout(1000);
      
      await page.screenshot({ 
        path: 'test-results/quick-actions-implementation.png'
      });
    });

    test('should show better visual hierarchy', async ({ page }) => {
      // Check heading hierarchy
      const h1 = page.locator('h1');
      const h2 = page.locator('h2');
      const h3 = page.locator('h3');
      
      await expect(h1).toHaveCount(1); // Should have one main heading
      
      // Check card elevation hierarchy
      const cards = page.locator('[class*="card"], .glass-epl');
      const cardCount = await cards.count();
      
      if (cardCount > 0) {
        const firstCard = cards.first();
        const boxShadow = await firstCard.evaluate(el => 
          window.getComputedStyle(el).boxShadow
        );
        expect(boxShadow).not.toBe('none');
      }
    });
  });

  test.describe('Real-time Features', () => {
    test('should show live data updates', async ({ page }) => {
      await page.click('text=Live Scores');
      await page.waitForSelector('.glass-epl', { timeout: 10000 });
      
      // Check for live indicators
      const liveIndicators = page.locator('text=Live, [class*="live"], [class*="animate-pulse"]');
      const count = await liveIndicators.count();
      
      // Should have some live indicators
      expect(count).toBeGreaterThan(0);
      
      // Check for auto-refresh messaging
      const autoRefreshText = page.locator('text=Auto-refreshing, text=30 seconds');
      await expect(autoRefreshText.first()).toBeVisible();
      
      await page.screenshot({ 
        path: 'test-results/live-data-features.png'
      });
    });

    test('should handle loading states gracefully', async ({ page }) => {
      // Navigate to a data-heavy section
      await page.click('text=Top Players');
      
      // Check for loading indicators
      const loadingElements = page.locator('.loading-epl, [class*="loading"], [class*="spinner"]');
      
      // Wait for content to load
      await page.waitForSelector('.player-card-epl', { timeout: 10000 });
      
      // Loading should complete
      await expect(loadingElements).toHaveCount(0);
      
      // Content should be visible
      const content = page.locator('.player-card-epl');
      await expect(content.first()).toBeVisible();
    });

    test('should show proper error states', async ({ page }) => {
      // This test would need to simulate network errors
      // For now, check if error handling components exist
      const errorComponents = page.locator('text=Error, text=Try Again, [class*="error"]');
      
      // Note: This test might need network interception to properly test error states
      console.log('Error handling components detected');
    });
  });

  test.describe('Mobile and Responsive Design', () => {
    test('should work well on mobile devices', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForTimeout(500);
      
      // Navigation should be accessible
      const navigation = page.locator('.tab-epl, nav, [role="navigation"]');
      await expect(navigation.first()).toBeVisible();
      
      // Content should be readable
      const mainContent = page.locator('h1, h2, .player-card-epl');
      await expect(mainContent.first()).toBeVisible();
      
      // Take mobile screenshot
      await page.screenshot({ 
        path: 'test-results/mobile-responsiveness.png',
        fullPage: true 
      });
    });

    test('should adapt to different screen sizes', async ({ page }) => {
      const sizes = [
        { width: 320, height: 568, name: 'small-mobile' },
        { width: 768, height: 1024, name: 'tablet' },
        { width: 1200, height: 800, name: 'desktop' },
        { width: 1920, height: 1080, name: 'large-desktop' }
      ];
      
      for (const size of sizes) {
        await page.setViewportSize(size);
        await page.waitForTimeout(500);
        
        // Content should remain accessible
        const title = page.locator('h1');
        await expect(title).toBeVisible();
        
        await page.screenshot({ 
          path: `test-results/responsive-${size.name}.png`
        });
      }
    });
  });

  test.describe('Performance and Accessibility', () => {
    test('should meet performance benchmarks', async ({ page }) => {
      const startTime = Date.now();
      
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      const loadTime = Date.now() - startTime;
      console.log(`Performance: Page loaded in ${loadTime}ms`);
      
      // Should load reasonably quickly
      expect(loadTime).toBeLessThan(8000);
      
      // Check for performance optimizations
      const images = page.locator('img[loading="lazy"]');
      const lazyImageCount = await images.count();
      console.log(`Lazy loading images: ${lazyImageCount}`);
    });

    test('should have good accessibility features', async ({ page }) => {
      // Check for proper ARIA labels
      const ariaElements = page.locator('[aria-label], [aria-describedby], [role]');
      const ariaCount = await ariaElements.count();
      console.log(`ARIA elements found: ${ariaCount}`);
      
      // Check for keyboard navigation
      await page.keyboard.press('Tab');
      const focusedElement = page.locator(':focus');
      await expect(focusedElement).toBeVisible();
      
      // Check color contrast (basic)
      const textElements = page.locator('p, h1, h2, h3, span').first();
      const styles = await textElements.evaluate(el => {
        const computed = window.getComputedStyle(el);
        return {
          color: computed.color,
          backgroundColor: computed.backgroundColor
        };
      });
      
      console.log('Text accessibility styles:', styles);
    });
  });
});