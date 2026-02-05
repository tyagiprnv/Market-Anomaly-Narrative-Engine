/**
 * Main application layout with header and navigation
 */

import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { SkipLink } from '../common';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gray-900">
      <SkipLink />
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 shadow-lg" role="banner">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo and title */}
            <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 lg:flex-none">
              <Link to="/" className="flex items-center gap-2 sm:gap-3 hover:opacity-80 transition-opacity min-w-0">
                <div className="w-8 h-8 flex-shrink-0 bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg flex items-center justify-center">
                  <svg
                    className="w-5 h-5 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                    />
                  </svg>
                </div>
                <h1 className="text-base sm:text-xl font-bold text-gray-100 truncate hidden sm:block">
                  Market Anomaly Narrative Engine
                </h1>
                <h1 className="text-base font-bold text-gray-100 sm:hidden">
                  MANE
                </h1>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1" role="navigation" aria-label="Main navigation">
              <Link
                to="/"
                className={`px-3 lg:px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive('/')
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }`}
              >
                Dashboard
              </Link>
              <Link
                to="/history"
                className={`px-3 lg:px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive('/history')
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }`}
              >
                History
              </Link>
              <Link
                to="/charts"
                className={`px-3 lg:px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  location.pathname.startsWith('/charts')
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }`}
              >
                Charts
              </Link>
            </nav>

            {/* Desktop User menu */}
            <div className="hidden md:flex items-center gap-2 lg:gap-4">
              <span className="text-sm text-gray-400 truncate max-w-[150px] lg:max-w-none" title={user?.email}>
                {user?.email}
              </span>
              <button
                onClick={logout}
                className="px-3 lg:px-4 py-2 text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700 rounded-md transition-colors whitespace-nowrap"
              >
                Logout
              </button>
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              aria-label="Toggle menu"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                {isMobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>

          {/* Mobile menu */}
          {isMobileMenuOpen && (
            <nav className="md:hidden border-t border-gray-700 py-3 space-y-1" role="navigation" aria-label="Mobile navigation">
              <Link
                to="/"
                onClick={() => setIsMobileMenuOpen(false)}
                className={`block px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive('/')
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }`}
              >
                Dashboard
              </Link>
              <Link
                to="/history"
                onClick={() => setIsMobileMenuOpen(false)}
                className={`block px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive('/history')
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }`}
              >
                History
              </Link>
              <Link
                to="/charts"
                onClick={() => setIsMobileMenuOpen(false)}
                className={`block px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  location.pathname.startsWith('/charts')
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }`}
              >
                Charts
              </Link>
              <div className="border-t border-gray-700 pt-3 mt-3">
                <div className="px-4 py-2 text-sm text-gray-400 truncate">{user?.email}</div>
                <button
                  onClick={() => {
                    logout();
                    setIsMobileMenuOpen(false);
                  }}
                  className="block w-full text-left px-4 py-2 text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700 rounded-md transition-colors"
                >
                  Logout
                </button>
              </div>
            </nav>
          )}
        </div>
      </header>

      {/* Main content */}
      <main
        id="main-content"
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8"
        role="main"
      >
        {children}
      </main>
    </div>
  );
}
