/**
 * Filter and sort an array of album objects.
 *
 * @param {Array}  albums     - Full album list from data.json
 * @param {string} searchTerm - Free-text search (matches artist or album name)
 * @param {Object} filters    - { year?: string, picker?: string, sortBy?: string }
 * @returns {Array} Filtered and sorted albums
 */
export function filterAndSort(albums, searchTerm = '', filters = {}) {
  let results = [...albums]

  // Free-text search across artist and album name
  if (searchTerm.trim()) {
    const term = searchTerm.toLowerCase()
    results = results.filter(a =>
      a.artist.toLowerCase().includes(term) ||
      a.album.toLowerCase().includes(term)
    )
  }

  // Filter by release decade (e.g. 2020 matches years 2020-2029)
  if (filters.decade) {
    const decade = Number(filters.decade)
    results = results.filter(a => {
      const y = Number(a.year)
      return y >= decade && y < decade + 10
    })
  }

  // Sort
  const sortBy = filters.sortBy || 'pick_number'
  results.sort((a, b) => {
    if (sortBy === 'pick_number') return a.pick_number - b.pick_number
    if (sortBy === 'artist')     return a.artist.localeCompare(b.artist)
    if (sortBy === 'album')      return a.album.localeCompare(b.album)
    if (sortBy === 'year')       return Number(a.year) - Number(b.year)
    return 0
  })

  return results
}

/** Return unique sorted values for a given field (used to populate filter dropdowns). */
export function uniqueValues(albums, field) {
  return [...new Set(albums.map(a => a[field]).filter(Boolean))].sort()
}

/** Return unique decades (e.g. 2020, 2010, 2000) derived from album release years, sorted newest first. */
export function uniqueDecades(albums) {
  return [...new Set(
    albums.map(a => a.year).filter(Boolean).map(y => Math.floor(Number(y) / 10) * 10)
  )].sort((a, b) => b - a)
}

/**
 * Wrapper around filterAndSort that accepts a unified options object.
 * sortBy in options is a fallback when filters.sortBy is not set.
 * direction: 'asc' | 'desc' — reverses the sorted result when 'desc'.
 */
export function processAlbums(albums, { searchTerm = '', filters = {}, sortBy = 'pick_number', direction = 'asc' } = {}) {
  const effectiveSortBy = filters.sortBy || sortBy
  const effectiveDirection = filters.sortDir || direction
  const results = filterAndSort(albums, searchTerm, { ...filters, sortBy: effectiveSortBy })
  return effectiveDirection === 'desc' ? results.reverse() : results
}

/**
 * Group an array of albums by pick year (derived from picked_at field).
 * Returns an object keyed by year string, e.g. { "2025": [...], "2026": [...] }.
 */
export function groupByYear(albums) {
  return albums.reduce((acc, album) => {
    const year = album.picked_at ? String(album.picked_at).slice(0, 4) : 'Unknown'
    if (!acc[year]) acc[year] = []
    acc[year].push(album)
    return acc
  }, {})
}
