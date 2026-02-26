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

  // Filter by release year
  if (filters.year) {
    results = results.filter(a => String(a.year) === String(filters.year))
  }

  // Filter by picker (who submitted it)
  if (filters.picker) {
    results = results.filter(a =>
      a.picker.toLowerCase() === filters.picker.toLowerCase()
    )
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
