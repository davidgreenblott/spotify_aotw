import { useState } from 'react'
import AlbumGrid from '../components/AlbumGrid'
import SearchBar from '../components/SearchBar'
import FilterBar from '../components/FilterBar'
import { useAlbums } from '../hooks/useAlbums'

export default function PicksPage() {
  const { albums, loading, error } = useAlbums()
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState({})

  if (loading) return <div className="status">Loading albums...</div>
  if (error)   return <div className="status error">Failed to load albums.</div>

  return (
    <>
      <div className="controls">
        <SearchBar value={searchTerm} onChange={setSearchTerm} />
        <FilterBar filters={filters} onChange={setFilters} albums={albums} />
      </div>
      <main>
        <AlbumGrid albums={albums} searchTerm={searchTerm} filters={filters} />
      </main>
    </>
  )
}
