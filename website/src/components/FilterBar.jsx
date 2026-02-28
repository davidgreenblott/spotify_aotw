import { useAlbumMetadata } from '../hooks/useAlbums'
import './FilterBar.css'

export default function FilterBar({ filters, onChange, albums }) {
  const { decades } = useAlbumMetadata(albums)

  function set(key, value) {
    onChange({ ...filters, [key]: value || undefined })
  }

  function handleSort(combined) {
    const [field, dir] = combined.split(':')
    onChange({ ...filters, sortBy: field, sortDir: dir })
  }

  function clearFilters() {
    onChange({})
  }

  const hasActiveFilters = Object.values(filters).some(Boolean)
  const sortValue = `${filters.sortBy || 'pick_number'}:${filters.sortDir || 'desc'}`

  return (
    <div className="filter-bar">
      <div className="filter-group">
        <label htmlFor="decade-filter">Decade</label>
        <select id="decade-filter" value={filters.decade || ''} onChange={e => set('decade', e.target.value)}>
          <option value="">All decades</option>
          {decades.map(d => <option key={d} value={d}>{d}s</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="sort-select">Sort by</label>
        <select id="sort-select" value={sortValue} onChange={e => handleSort(e.target.value)}>
          <option value="pick_number:desc">Pick # ↓</option>
          <option value="pick_number:asc">Pick # ↑</option>
          <option value="artist:asc">Artist A→Z</option>
          <option value="artist:desc">Artist Z→A</option>
          <option value="album:asc">Album A→Z</option>
          <option value="album:desc">Album Z→A</option>
          <option value="year:desc">Release year ↓</option>
          <option value="year:asc">Release year ↑</option>
        </select>
      </div>

      {hasActiveFilters && (
        <button className="clear-filters" onClick={clearFilters}>Clear filters</button>
      )}
    </div>
  )
}
