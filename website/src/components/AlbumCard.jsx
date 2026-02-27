export default function AlbumCard({ album }) {
  const { pick_number, artist, album: title, year, artwork_url, spotify_url, picked_at, picker } = album

  return (
    <a
      className="album-card"
      href={spotify_url}
      target="_blank"
      rel="noopener noreferrer"
      title={`${artist} — ${title}`}
    >
      <img
        src={artwork_url || '/cd-placeholder.svg'}
        alt={`${artist} - ${title}`}
        loading="lazy"
        onError={e => { e.target.src = '/cd-placeholder.svg' }}
      />
      <div className="album-card__info">
        <span className="album-card__pick">#{pick_number}</span>
        <p className="album-card__title">{title}</p>
        <p className="album-card__artist">{artist}</p>
        <p className="album-card__meta">{year}{picker ? ` · ${picker}` : ''}</p>
      </div>
    </a>
  )
}
