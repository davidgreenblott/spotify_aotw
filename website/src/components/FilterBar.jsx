import { uniqueValues } from '../utils/filterSort'

export default function FilterBar({ filters, onChange, albums }) {
  const years   = uniqueValues(albums, 'year')
  const pickers = uniqueValues(albums, 'picker')

  function set(key, value) {
    onChange({ ...filters, [key]: value || undefined })
  }

  return (
    <div className="filter-bar">
      <select value={filters.year || ''} onChange={e => set('year', e.target.value)}>
        <option value="">All years</option>
        {years.map(y => <option key={y} value={y}>{y}</option>)}
      </select>

      <select value={filters.picker || ''} onChange={e => set('picker', e.target.value)}>
        <option value="">All pickers</option>
        {pickers.map(p => <option key={p} value={p}>{p}</option>)}
      </select>

      <select value={filters.sortBy || 'pick_number'} onChange={e => set('sortBy', e.target.value)}>
        <option value="pick_number">Sort: Pick #</option>
        <option value="artist">Sort: Artist</option>
        <option value="album">Sort: Album</option>
        <option value="year">Sort: Year</option>
      </select>
    </div>
  )
}
