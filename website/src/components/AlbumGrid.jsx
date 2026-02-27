import { useState, useMemo } from 'react'
import AlbumCard from './AlbumCard'
import { processAlbums, groupByYear } from '../utils/filterSort'
import './AlbumGrid.css'

function AlbumGrid({ albums, searchTerm, filters, sortBy = 'date', direction = 'desc' }) {
  const [expandedYears, setExpandedYears] = useState(new Set())

  // Process albums (filter, search, sort)
  const processedAlbums = useMemo(() => {
    return processAlbums(albums, { searchTerm, filters, sortBy, direction })
  }, [albums, searchTerm, filters, sortBy, direction])

  // Group by pick year
  const albumsByYear = useMemo(() => {
    return groupByYear(processedAlbums)
  }, [processedAlbums])

  const years = Object.keys(albumsByYear).sort((a, b) => b - a)

  const toggleYear = (year) => {
    const newExpanded = new Set(expandedYears)
    if (newExpanded.has(year)) {
      newExpanded.delete(year)
    } else {
      newExpanded.add(year)
    }
    setExpandedYears(newExpanded)
  }

  const expandAll = () => setExpandedYears(new Set(years))
  const collapseAll = () => setExpandedYears(new Set())

  if (processedAlbums.length === 0) {
    return (
      <div className="empty-state">
        <p>No albums found</p>
      </div>
    )
  }

  // Flat grid for small result sets
  if (processedAlbums.length < 50) {
    return (
      <div className="album-grid-container">
        <div className="album-grid">
          {processedAlbums.map(album => (
            <AlbumCard key={album.spotify_album_id} album={album} />
          ))}
        </div>
      </div>
    )
  }

  // Grouped by year mode
  return (
    <div className="album-grid-container">
      <div className="grid-controls">
        <button onClick={expandAll}>Expand All</button>
        <button onClick={collapseAll}>Collapse All</button>
        <span>{processedAlbums.length} albums</span>
      </div>

      {years.map(year => {
        const yearAlbums = albumsByYear[year]
        const isExpanded = expandedYears.has(year)

        return (
          <div key={year} className="year-group">
            <div className="year-header" onClick={() => toggleYear(year)}>
              <h2>
                <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
                {year}
                <span className="year-count">({yearAlbums.length})</span>
              </h2>
            </div>

            {isExpanded && (
              <div className="album-grid">
                {yearAlbums.map(album => (
                  <AlbumCard key={album.spotify_album_id} album={album} />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default AlbumGrid
