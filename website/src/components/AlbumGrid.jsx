import AlbumCard from './AlbumCard'
import { filterAndSort } from '../utils/filterSort'

export default function AlbumGrid({ albums, searchTerm, filters }) {
  const visible = filterAndSort(albums, searchTerm, filters)

  if (visible.length === 0) {
    return <p className="no-results">No albums match your search.</p>
  }

  return (
    <div className="album-grid">
      {visible.map(album => (
        <AlbumCard key={album.spotify_album_id} album={album} />
      ))}
    </div>
  )
}
