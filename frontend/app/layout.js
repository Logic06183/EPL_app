import './globals.css'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'FPL Prediction Dashboard',
  description: 'AI-Powered Fantasy Premier League Optimization and Predictions',
  keywords: 'FPL, Fantasy Premier League, AI, predictions, optimization, football',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gradient-to-br from-blue-400 via-purple-500 to-pink-500">
          {children}
        </div>
      </body>
    </html>
  )
}