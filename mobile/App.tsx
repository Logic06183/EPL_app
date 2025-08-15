import React, { useEffect } from 'react'
import { StatusBar } from 'expo-status-bar'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import * as Notifications from 'expo-notifications'
import { Ionicons } from '@expo/vector-icons'

// Screens
import { LoginScreen } from './src/screens/LoginScreen'
import { RegisterScreen } from './src/screens/RegisterScreen'
import { DashboardScreen } from './src/screens/DashboardScreen'
import { PredictionsScreen } from './src/screens/PredictionsScreen'
import { OptimizerScreen } from './src/screens/OptimizerScreen'
import { AlertsScreen } from './src/screens/AlertsScreen'
import { ProfileScreen } from './src/screens/ProfileScreen'

// Store & Hooks
import { useAuthStore } from './src/stores/authStore'
import { setupNotifications } from './src/services/notifications'

const Stack = createNativeStackNavigator()
const Tab = createBottomTabNavigator()
const queryClient = new QueryClient()

// Configure notifications
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
})

function AuthStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: '#10b981',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <Stack.Screen 
        name="Login" 
        component={LoginScreen}
        options={{ title: 'Sign In' }}
      />
      <Stack.Screen 
        name="Register" 
        component={RegisterScreen}
        options={{ title: 'Create Account' }}
      />
    </Stack.Navigator>
  )
}

function MainTabs() {
  const { user } = useAuthStore()
  const isPremium = user?.tier === 'premium' || user?.tier === 'elite'

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap = 'home'

          if (route.name === 'Dashboard') {
            iconName = focused ? 'home' : 'home-outline'
          } else if (route.name === 'Predictions') {
            iconName = focused ? 'trending-up' : 'trending-up-outline'
          } else if (route.name === 'Optimizer') {
            iconName = focused ? 'trophy' : 'trophy-outline'
          } else if (route.name === 'Alerts') {
            iconName = focused ? 'notifications' : 'notifications-outline'
          } else if (route.name === 'Profile') {
            iconName = focused ? 'person' : 'person-outline'
          }

          return <Ionicons name={iconName} size={size} color={color} />
        },
        tabBarActiveTintColor: '#10b981',
        tabBarInactiveTintColor: 'gray',
        headerStyle: {
          backgroundColor: '#10b981',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      })}
    >
      <Tab.Screen 
        name="Dashboard" 
        component={DashboardScreen}
        options={{ 
          title: 'Dashboard',
          tabBarBadge: undefined // Add badge for notifications
        }}
      />
      <Tab.Screen 
        name="Predictions" 
        component={PredictionsScreen}
        options={{ 
          title: 'Predictions',
          tabBarBadge: !isPremium ? '🔒' : undefined
        }}
      />
      <Tab.Screen 
        name="Optimizer" 
        component={OptimizerScreen}
        options={{ title: 'Team Optimizer' }}
      />
      <Tab.Screen 
        name="Alerts" 
        component={AlertsScreen}
        options={{ 
          title: 'Alerts',
          tabBarBadge: 3 // Show unread count
        }}
      />
      <Tab.Screen 
        name="Profile" 
        component={ProfileScreen}
        options={{ title: 'Profile' }}
      />
    </Tab.Navigator>
  )
}

export default function App() {
  const { user, checkAuth } = useAuthStore()

  useEffect(() => {
    // Check authentication status on app launch
    checkAuth()
    
    // Setup push notifications
    setupNotifications()
  }, [])

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <NavigationContainer>
            <StatusBar style="light" />
            {user ? <MainTabs /> : <AuthStack />}
          </NavigationContainer>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
}