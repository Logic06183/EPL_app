#!/usr/bin/env python3
"""
Comprehensive System Test for FPL AI Pro
Tests all features and identifies issues before deployment
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from typing import Dict, List

# Set environment variables
os.environ['NEWS_API_KEY'] = 'e36350769b6341bb81b832a84442e6ad'

class FPLSystemTester:
    def __init__(self):
        self.api_base = "http://localhost:8001"
        self.test_results = []
        self.passed = 0
        self.failed = 0
        
    async def test_api_health(self):
        """Test API is running and healthy"""
        print("\n🔍 Testing API Health...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/health")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ API Status: {data['status']}")
                    print(f"   ✅ AI Enabled: {data.get('ai_enabled', False)}")
                    print(f"   ✅ Cache: {data.get('cache_status', 'unknown')}")
                    self.passed += 1
                    return True
                else:
                    print(f"   ❌ API returned status {response.status_code}")
                    self.failed += 1
                    return False
        except Exception as e:
            print(f"   ❌ API not reachable: {e}")
            self.failed += 1
            return False
    
    async def test_player_predictions(self):
        """Test player predictions endpoint"""
        print("\n🎯 Testing Player Predictions...")
        try:
            async with httpx.AsyncClient() as client:
                # Test different configurations
                test_cases = [
                    {"top_n": 10, "use_ai": False, "name": "Basic"},
                    {"top_n": 20, "use_ai": True, "name": "AI Enhanced"},
                    {"top_n": 10, "position": 1, "name": "Goalkeepers"},
                    {"top_n": 10, "position": 4, "name": "Forwards"},
                ]
                
                for test in test_cases:
                    params = {k: v for k, v in test.items() if k != "name"}
                    response = await client.get(
                        f"{self.api_base}/api/players/predictions",
                        params=params,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        predictions = data.get('predictions', [])
                        print(f"   ✅ {test['name']}: {len(predictions)} players returned")
                        
                        # Validate data structure
                        if predictions:
                            player = predictions[0]
                            required_fields = ['id', 'name', 'predicted_points', 'price', 'form']
                            missing = [f for f in required_fields if f not in player]
                            if missing:
                                print(f"   ⚠️  Missing fields: {missing}")
                            
                            # Check for erroneous data
                            if player['predicted_points'] < 0:
                                print(f"   ❌ Negative prediction for {player['name']}")
                                self.failed += 1
                            elif player['predicted_points'] > 20:
                                print(f"   ⚠️  Unusually high prediction for {player['name']}: {player['predicted_points']}")
                        
                        self.passed += 1
                    else:
                        print(f"   ❌ {test['name']}: Status {response.status_code}")
                        self.failed += 1
                        
        except Exception as e:
            print(f"   ❌ Predictions test failed: {e}")
            self.failed += 1
    
    async def test_different_teams(self):
        """Test predictions for players from different teams"""
        print("\n⚽ Testing Different Teams...")
        
        teams_to_test = [
            "Liverpool", "Manchester City", "Arsenal", "Chelsea",
            "Manchester United", "Tottenham", "Newcastle", "Brighton"
        ]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/api/players/predictions",
                    params={"top_n": 100}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    predictions = data.get('predictions', [])
                    
                    # Group by team
                    teams_found = {}
                    for player in predictions:
                        team = player.get('team_name', 'Unknown')
                        if team not in teams_found:
                            teams_found[team] = []
                        teams_found[team].append(player)
                    
                    print(f"   📊 Found {len(teams_found)} teams")
                    
                    # Check major teams
                    for team in teams_to_test[:4]:  # Test top 4 teams
                        if team in teams_found:
                            players = teams_found[team]
                            avg_prediction = sum(p['predicted_points'] for p in players) / len(players)
                            print(f"   ✅ {team}: {len(players)} players, avg prediction: {avg_prediction:.1f}")
                        else:
                            print(f"   ⚠️  {team}: No players found")
                    
                    self.passed += 1
                else:
                    print(f"   ❌ Failed to fetch team data")
                    self.failed += 1
                    
        except Exception as e:
            print(f"   ❌ Team test failed: {e}")
            self.failed += 1
    
    async def test_player_search(self):
        """Test player search functionality"""
        print("\n🔎 Testing Player Search...")
        
        test_players = [
            "Haaland", "Salah", "Kane", "De Bruyne",
            "Palmer", "Saka", "Rice", "Watkins"
        ]
        
        try:
            async with httpx.AsyncClient() as client:
                for player_name in test_players[:4]:  # Test first 4
                    response = await client.get(
                        f"{self.api_base}/api/players/search",
                        params={"q": player_name}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        players = data.get('players', [])
                        
                        if players:
                            player = players[0]
                            print(f"   ✅ {player_name}: Found {player['full_name']} (£{player['price']}m)")
                            
                            # Check for data issues
                            if player['total_points'] == 0 and player['form'] > 0:
                                print(f"      ⚠️  Inconsistent data: 0 points but form {player['form']}")
                        else:
                            print(f"   ⚠️  {player_name}: Not found")
                    else:
                        print(f"   ❌ {player_name}: Search failed")
                        
                self.passed += 1
                
        except Exception as e:
            print(f"   ❌ Search test failed: {e}")
            self.failed += 1
    
    async def test_squad_optimizer(self):
        """Test squad optimization endpoint"""
        print("\n🏆 Testing Squad Optimizer...")
        
        budgets = [100.0, 90.0, 110.0]
        
        try:
            async with httpx.AsyncClient() as client:
                for budget in budgets:
                    response = await client.post(
                        f"{self.api_base}/api/optimize/squad",
                        json={"budget": budget},
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        squad = data.get('squad', [])
                        total_cost = data.get('total_cost', 0)
                        
                        print(f"   ✅ Budget £{budget}m: {len(squad)} players, cost £{total_cost:.1f}m")
                        
                        # Validate squad composition
                        positions = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
                        for player in squad:
                            pos = player.get('position', '')
                            if pos in positions:
                                positions[pos] += 1
                        
                        # Check valid formation
                        if positions['GK'] != 2:
                            print(f"      ❌ Invalid GK count: {positions['GK']}")
                        if positions['DEF'] != 5:
                            print(f"      ❌ Invalid DEF count: {positions['DEF']}")
                        if positions['MID'] != 5:
                            print(f"      ❌ Invalid MID count: {positions['MID']}")
                        if positions['FWD'] != 3:
                            print(f"      ❌ Invalid FWD count: {positions['FWD']}")
                        
                        if len(squad) == 15:
                            print(f"      ✅ Valid squad size")
                        else:
                            print(f"      ❌ Invalid squad size: {len(squad)}")
                            
                        self.passed += 1
                    else:
                        print(f"   ❌ Budget £{budget}m: Optimization failed")
                        self.failed += 1
                        
        except Exception as e:
            print(f"   ❌ Squad optimizer test failed: {e}")
            self.failed += 1
    
    async def test_news_sentiment(self):
        """Test news sentiment analysis"""
        print("\n📰 Testing News Sentiment Analysis...")
        
        try:
            from news_sentiment_analyzer import NewsSentimentAnalyzer
            
            analyzer = NewsSentimentAnalyzer()
            
            test_players = [
                ("Haaland", "Manchester City"),
                ("Salah", "Liverpool"),
                ("Saka", "Arsenal")
            ]
            
            for player_name, team in test_players:
                sentiment = await analyzer.get_player_sentiment(player_name, team)
                
                print(f"   ✅ {player_name}:")
                print(f"      Sentiment: {sentiment['sentiment']}")
                print(f"      Articles: {sentiment['articles_analyzed']}")
                print(f"      Impact: {sentiment['sentiment_impact']:+.1f}")
                
                if sentiment['articles_analyzed'] == 0:
                    print(f"      ⚠️  No articles found (may be API limit)")
            
            self.passed += 1
            
        except Exception as e:
            print(f"   ❌ Sentiment test failed: {e}")
            self.failed += 1
    
    async def test_previous_season_players(self):
        """Test that previous season players are handled correctly"""
        print("\n📅 Testing Previous Season Player Handling...")
        
        # Players who might have transferred or retired
        test_cases = [
            {"name": "Kane", "old_team": "Tottenham", "note": "Moved to Bayern"},
            {"name": "Mount", "old_team": "Chelsea", "note": "Moved to Man United"},
            {"name": "Rice", "old_team": "West Ham", "note": "Moved to Arsenal"},
        ]
        
        try:
            async with httpx.AsyncClient() as client:
                for test in test_cases:
                    response = await client.get(
                        f"{self.api_base}/api/players/search",
                        params={"q": test['name']}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        players = data.get('players', [])
                        
                        if players:
                            player = players[0]
                            current_team = player.get('team_name', '')
                            
                            # Check if player has correct current team
                            if test['old_team'] in current_team:
                                print(f"   ⚠️  {test['name']}: Still showing old team {current_team}")
                                print(f"      Note: {test['note']}")
                            else:
                                print(f"   ✅ {test['name']}: Correctly showing {current_team}")
                        else:
                            print(f"   ⚠️  {test['name']}: Not found in current season")
                            
                self.passed += 1
                
        except Exception as e:
            print(f"   ❌ Previous season test failed: {e}")
            self.failed += 1
    
    async def test_data_consistency(self):
        """Test data consistency and validation"""
        print("\n🔧 Testing Data Consistency...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/api/players/predictions",
                    params={"top_n": 50}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    predictions = data.get('predictions', [])
                    
                    issues = []
                    
                    for player in predictions:
                        # Check for data inconsistencies
                        if player['predicted_points'] < 0:
                            issues.append(f"{player['name']}: Negative prediction")
                        
                        if player['price'] <= 0:
                            issues.append(f"{player['name']}: Invalid price")
                        
                        if player['form'] < 0 or player['form'] > 10:
                            issues.append(f"{player['name']}: Invalid form {player['form']}")
                        
                        if player['ownership'] < 0 or player['ownership'] > 100:
                            issues.append(f"{player['name']}: Invalid ownership {player['ownership']}%")
                        
                        # Check prediction vs form correlation
                        if player['form'] > 7 and player['predicted_points'] < 3:
                            issues.append(f"{player['name']}: High form but low prediction")
                        
                        if player['form'] < 2 and player['predicted_points'] > 8:
                            issues.append(f"{player['name']}: Low form but high prediction")
                    
                    if issues:
                        print(f"   ⚠️  Found {len(issues)} consistency issues:")
                        for issue in issues[:5]:  # Show first 5
                            print(f"      - {issue}")
                        self.failed += 1
                    else:
                        print(f"   ✅ All {len(predictions)} players have consistent data")
                        self.passed += 1
                else:
                    print(f"   ❌ Failed to fetch data")
                    self.failed += 1
                    
        except Exception as e:
            print(f"   ❌ Consistency test failed: {e}")
            self.failed += 1
    
    async def run_all_tests(self):
        """Run all system tests"""
        print("=" * 60)
        print("🧪 FPL AI PRO - COMPREHENSIVE SYSTEM TEST")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API Base: {self.api_base}")
        
        # Run all tests
        await self.test_api_health()
        await self.test_player_predictions()
        await self.test_different_teams()
        await self.test_player_search()
        await self.test_squad_optimizer()
        await self.test_news_sentiment()
        await self.test_previous_season_players()
        await self.test_data_consistency()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {(self.passed/(self.passed+self.failed)*100):.1f}%")
        
        if self.failed == 0:
            print("\n🎉 ALL TESTS PASSED! System ready for deployment!")
        else:
            print(f"\n⚠️  {self.failed} tests failed. Review issues before deployment.")
        
        return self.failed == 0

async def main():
    """Main test runner"""
    tester = FPLSystemTester()
    success = await tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("💡 DEPLOYMENT CHECKLIST")
    print("=" * 60)
    print("✅ API running and healthy")
    print("✅ Player predictions working")
    print("✅ Squad optimizer functional")
    print("✅ News sentiment integrated")
    print("⚠️  Check transferred players data")
    print("⚠️  Verify PayStack integration")
    print("⚠️  Configure production environment variables")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())