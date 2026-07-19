import { Link, NavLink, Navigate, Route, Routes } from 'react-router-dom';

import { ArchitectureDetailPage } from './features/architectures/ArchitectureDetailPage';
import { ArchitecturesPage } from './features/architectures/ArchitecturesPage';
import { RecommendationsPage } from './features/recommendations/RecommendationsPage';
import { ScrapingPage } from './features/scraping/ScrapingPage';

/** App shell: full-width top navigation bar plus routed feature pages. */
export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/architectures" className="brand">
            <svg
              className="brand-logo"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M12 2 2 7l10 5 10-5-10-5Z" />
              <path d="m2 17 10 5 10-5" />
              <path d="m2 12 10 5 10-5" />
            </svg>
            <span className="brand-name">
              Cloud Architecture <strong>Recommender</strong>
            </span>
          </Link>
          <nav className="app-nav">
            <NavLink to="/architectures">Architectures</NavLink>
            <NavLink to="/recommendations">Recommendations</NavLink>
            <NavLink to="/scraping">Scraping</NavLink>
          </nav>
        </div>
      </header>
      <main className="app-main">
        <div className="app-container">
          <Routes>
            <Route path="/" element={<Navigate to="/architectures" replace />} />
            <Route path="/architectures" element={<ArchitecturesPage />} />
            <Route path="/architectures/:slug" element={<ArchitectureDetailPage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/scraping" element={<ScrapingPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
