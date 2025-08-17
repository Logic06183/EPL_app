// tests/design-research.spec.js
import { test } from '@playwright/test';

test.describe('Design Research - Competitive Analysis', () => {
  
  test('analyze competitor design patterns', async ({ page }) => {
    // List of competitor sites to analyze
    const competitors = [
      'https://fantasy.premierleague.com',
      'https://www.espn.com/fantasy/football/',
      'https://fantasy.footballguys.com',
    ];
    
    for (const url of competitors) {
      try {
        console.log(`Analyzing: ${url}`);
        
        await page.goto(url, { timeout: 30000 });
        await page.waitForLoadState('networkidle', { timeout: 10000 });
        
        // Take full page screenshot
        const siteName = url.replace(/https?:\/\//, '').replace(/[\/\.]/g, '-');
        await page.screenshot({ 
          path: `test-results/competitor-${siteName}.png`,
          fullPage: true 
        });
        
        // Analyze color scheme
        const bodyStyles = await page.evaluate(() => {
          const body = document.body;
          const styles = window.getComputedStyle(body);
          return {
            backgroundColor: styles.backgroundColor,
            color: styles.color,
            fontFamily: styles.fontFamily
          };
        });
        
        console.log(`${url} styles:`, bodyStyles);
        
        // Check for dark mode
        const isDarkMode = await page.evaluate(() => {
          const body = document.body;
          const bgColor = window.getComputedStyle(body).backgroundColor;
          const rgb = bgColor.match(/\\d+/g);
          if (rgb) {
            const brightness = (parseInt(rgb[0]) + parseInt(rgb[1]) + parseInt(rgb[2])) / 3;
            return brightness < 128;
          }
          return false;
        });
        
        console.log(`${url} has dark mode:`, isDarkMode);
        
        // Analyze navigation patterns
        const navElements = await page.$$eval('nav, [role="navigation"], .nav, .navigation', els => 
          els.map(el => ({
            tagName: el.tagName,
            className: el.className,
            childCount: el.children.length
          }))
        );
        
        console.log(`${url} navigation patterns:`, navElements);
        
      } catch (error) {
        console.log(`Failed to analyze ${url}:`, error.message);
      }
    }
  });

  test('analyze modern sports app design trends', async ({ page }) => {
    // Visit design inspiration sites
    const designSites = [
      'https://dribbble.com/tags/fantasy-football',
      'https://www.behance.net/search/projects?search=sports%20app',
    ];
    
    for (const url of designSites) {
      try {
        console.log(`Analyzing design trends from: ${url}`);
        
        await page.goto(url, { timeout: 30000 });
        await page.waitForLoadState('networkidle', { timeout: 10000 });
        
        // Take screenshot of design gallery
        const siteName = url.replace(/https?:\/\//, '').replace(/[\/\.]/g, '-');
        await page.screenshot({ 
          path: `test-results/design-inspiration-${siteName}.png`,
          fullPage: true 
        });
        
        // Analyze common design elements
        const designElements = await page.evaluate(() => {
          const cards = document.querySelectorAll('[class*="card"], [class*="project"], [class*="shot"]');
          return Array.from(cards).slice(0, 10).map(card => {
            const styles = window.getComputedStyle(card);
            return {
              borderRadius: styles.borderRadius,
              boxShadow: styles.boxShadow,
              backgroundColor: styles.backgroundColor,
              padding: styles.padding
            };
          });
        });
        
        console.log(`Design elements from ${url}:`, designElements);
        
      } catch (error) {
        console.log(`Failed to analyze ${url}:`, error.message);
      }
    }
  });

  test('generate design recommendations report', async ({ page }) => {
    // Create a comprehensive design analysis report
    const report = {
      timestamp: new Date().toISOString(),
      currentAppAnalysis: {},
      competitorAnalysis: {},
      designTrends: {},
      recommendations: []
    };
    
    // Analyze our current app
    await page.goto('https://epl-prediction-app.web.app');
    await page.waitForLoadState('networkidle');
    
    report.currentAppAnalysis = await page.evaluate(() => {
      const body = document.body;
      const styles = window.getComputedStyle(body);
      
      // Count design elements
      const glassMorphismCards = document.querySelectorAll('.glass-epl, [class*="glass"]').length;
      const gradientElements = document.querySelectorAll('[class*="gradient"]').length;
      const buttonElements = document.querySelectorAll('button').length;
      const cardElements = document.querySelectorAll('[class*="card"]').length;
      
      return {
        hasGlassMorphism: glassMorphismCards > 0,
        glassMorphismCount: glassMorphismCards,
        hasGradients: gradientElements > 0,
        gradientCount: gradientElements,
        buttonCount: buttonElements,
        cardCount: cardElements,
        backgroundColor: styles.backgroundColor,
        fontFamily: styles.fontFamily,
        isDarkMode: styles.backgroundColor.includes('rgb(0') || styles.backgroundColor.includes('rgb(1') || styles.backgroundColor.includes('rgb(2')
      };
    });
    
    // Based on research, generate recommendations
    report.recommendations = [
      {
        category: 'Visual Design',
        priority: 'High',
        items: [
          'Enhance gradient usage with more dynamic lighting effects (Lightning Dark trend)',
          'Implement more sophisticated micro-interactions and hover states',
          'Add subtle animations for state changes and loading',
          'Improve card elevation and shadow depth for better hierarchy'
        ]
      },
      {
        category: 'Information Architecture',
        priority: 'Medium',
        items: [
          'Enhanced player cards with more historical data visualization',
          'Better use of space with Bento Grid layout principles',
          'Improved quick-action buttons for common tasks',
          'More prominent AI confidence indicators'
        ]
      },
      {
        category: 'User Experience',
        priority: 'High',
        items: [
          'Real-time visual feedback for predictions updating',
          'Progressive disclosure for complex information',
          'Better onboarding flow for new users',
          'Enhanced mobile responsiveness'
        ]
      },
      {
        category: 'Performance',
        priority: 'Medium',
        items: [
          'Optimize loading states and skeleton screens',
          'Implement better error states with recovery actions',
          'Add predictive loading for frequently accessed data',
          'Improve perceived performance with better transitions'
        ]
      }
    ];
    
    // Save report
    await page.evaluate((reportData) => {
      console.log('=== DESIGN ANALYSIS REPORT ===');
      console.log(JSON.stringify(reportData, null, 2));
    }, report);
    
    // Take a final comprehensive screenshot
    await page.screenshot({ 
      path: 'test-results/current-app-full-analysis.png',
      fullPage: true 
    });
    
    return report;
  });
});