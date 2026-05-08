import { Outlet, Link, useLocation } from 'react-router-dom'
import { BarChart3, Home, Cpu } from 'lucide-react'

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-semibold text-indigo-700 text-lg">
            <BarChart3 className="w-5 h-5" />
            FinModel Generator
          </Link>
          <nav className="flex items-center gap-4 text-sm text-gray-600">
            <Link
              to="/"
              className={`flex items-center gap-1 hover:text-indigo-700 transition-colors ${
                location.pathname === '/' ? 'text-indigo-700 font-medium' : ''
              }`}
            >
              <Home className="w-4 h-4" /> Projects
            </Link>
            <Link
              to="/llm-setup"
              className={`flex items-center gap-1.5 hover:text-indigo-700 transition-colors px-2.5 py-1.5 rounded-lg ${
                location.pathname === '/llm-setup'
                  ? 'text-indigo-700 font-medium bg-indigo-50'
                  : 'hover:bg-gray-50'
              }`}
            >
              <Cpu className="w-4 h-4" /> LLM Setup
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-gray-100 py-3 text-center text-xs text-gray-400">
        Financial Model Generator · Local-first · All data stays on your machine
      </footer>
    </div>
  )
}
