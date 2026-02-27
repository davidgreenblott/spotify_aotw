import { useAlbumMetadata } from '../hooks/useAlbums'
import './FilterBar.css'

export default function FilterBar({ filters, onChange, albums }) {
  const { years, artists, pickers } = useAlbumMetadata(albums)

  function set(key, value) {
    onChange({ ...filters, [key]: value || undefined })
  }

  function clearFilters() {
    onChange({})
  }

  const hasActiveFilters = Object.values(filters).some(Boolean)

  return (
    <div className="filter-bar">
      <div className="filter-group">
        <label htmlFor="year-filter">Year</label>
        <select id="year-filter" value={filters.year || ''} onChange={e => set('year', e.target.value)}>
          <option value="">All years</option>
          {years.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="artist-filter">Artist</label>
        <select id="artist-filter" value={filters.artist || ''} onChange={e => set('artist', e.target.value)}>
          <option value="">All artists</option>
          {artists.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="picker-filter">Picker</label>
        <select id="picker-filter" value={filters.picker || ''} onChange={e => set('picker', e.target.value)}>
          <option value="">All pickers</option>
          {pickers.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="sort-select">Sort by</label>
        <select id="sort-select" value={filters.sortBy || 'pick_number'} onChange={e => set('sortBy', e.target.value)}>
          <option value="pick_number">Pick #</option>
          <option value="artist">Artist</option>
          <option value="album">Album</option>
          <option value="year">Release year</option>
        </select>
      </div>

      {hasActiveFilters && (
        <button className="clear-filters" onClick={clearFilters}>Clear filters</button>
      )}
    </div>
  )
}
