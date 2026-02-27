import { useState } from 'react'
import AlbumGrid from './components/AlbumGrid'
import SearchBar from './components/SearchBar'
import FilterBar from './components/FilterBar'
import { useAlbums } from './hooks/useAlbums'
import './index.css'

function App() {
  const { albums, loading, error } = useAlbums()
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState({})

  if (loading) return <div className="status">Loading albums...</div>
  if (error)   return <div className="status error">Failed to load albums.</div>

  return (
    <div className="app">
      <header className="header">
        <h1>Album of the Week</h1>
        <div className="controls">
          <SearchBar value={searchTerm} onChange={setSearchTerm} />
          <FilterBar filters={filters} onChange={setFilters} albums={albums} />
        </div>
      </header>
      <main>
        <AlbumGrid albums={albums} searchTerm={searchTerm} filters={filters} />
      </main>
    </div>
  )
}

export default App
