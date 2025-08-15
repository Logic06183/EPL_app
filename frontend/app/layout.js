import './globals.css'
import './epl-theme.css'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'FPL AI Pro - Premier League Predictions',
  description: 'AI-Powered Fantasy Premier League predictions and optimization with real-time data',
  keywords: 'FPL, Fantasy Premier League, AI, predictions, optimization, football, EPL',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="⚽" />
      </head>
      <body className={inter.className}>
        {children}
      </body>
    </html>
  )
}