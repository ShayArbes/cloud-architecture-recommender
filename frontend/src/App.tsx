import { NavLink, Navigate, Route, Routes } from 'react-router-dom';

import { ArchitectureDetailPage } from './features/architectures/ArchitectureDetailPage';
import { ArchitecturesPage } from './features/architectures/ArchitecturesPage';
import { RecommendationsPage } from './features/recommendations/RecommendationsPage';
import { ScrapingPage } from './features/scraping/ScrapingPage';

/** App shell: top navigation plus routed feature pages. */
export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Cloud Architecture Recommender</h1>
        <nav className="app-nav">
          <NavLink to="/architectures">Architectures</NavLink>
          <NavLink to="/recommendations">Recommendations</NavLink>
          <NavLink to="/scraping">Scraping</NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/architectures" replace />} />
          <Route path="/architectures" element={<ArchitecturesPage />} />
          <Route path="/architectures/:slug" element={<ArchitectureDetailPage />} />
          <Route path="/recommendations" element={<RecommendationsPage />} />
          <Route path="/scraping" element={<ScrapingPage />} />
        </Routes>
      </main>
    </div>
  );
}
