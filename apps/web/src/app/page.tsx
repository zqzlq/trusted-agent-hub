'use client';

import { useState, useMemo, useEffect } from 'react';
import { fetchPackages, type Package } from '@/data/packages';
import SearchBar from '@/components/SearchBar';
import ScannerForm from '@/components/ScannerForm';
import PackageCard from '@/components/PackageCard';

export default function HomePage() {
  const [query, setQuery] = useState('');
  const [activeType, setActiveType] = useState('all');
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPackages()
      .then(setPackages)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();

    return packages.filter((pkg) => {
      if (activeType !== 'all' && pkg.type !== activeType) {
        return false;
      }

      if (!q) return true;

      const matchName = pkg.name.toLowerCase().includes(q);
      const matchDesc = pkg.description.toLowerCase().includes(q);
      const matchKeyword = pkg.keywords.some((kw) =>
        kw.toLowerCase().includes(q)
      );

      return matchName || matchDesc || matchKeyword;
    });
  }, [query, activeType, packages]);

  return (
    <div className="page-container">
      <SearchBar
        query={query}
        activeType={activeType}
        onQueryChange={setQuery}
        onTypeChange={setActiveType}
      />

      <ScannerForm />

      <p className="results-meta">
        {filtered.length} package{filtered.length !== 1 ? 's' : ''} found
      </p>

      {loading && (
        <div className="empty-state">
          <div className="empty-state-icon">&#x23F3;</div>
          <h3>Loading packages...</h3>
        </div>
      )}

      {error && (
        <div className="empty-state">
          <div className="empty-state-icon">&#x26A0;</div>
          <h3>Failed to load packages</h3>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <>
          <p className="results-meta">
            {filtered.length} package{filtered.length !== 1 ? 's' : ''} found
          </p>

          {filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">&#x1F50E;</div>
              <h3>No packages found</h3>
              <p>Try adjusting your search or filter criteria.</p>
            </div>
          ) : (
            <div className="package-grid">
              {filtered.map((pkg) => (
                <PackageCard key={pkg.id} pkg={pkg} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}