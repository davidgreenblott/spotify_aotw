function SpotifyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
    </svg>
  )
}

function AppleMusicIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M23.994 6.124a9.23 9.23 0 0 0-.24-2.19c-.317-1.31-1.062-2.31-2.18-3.043a5.022 5.022 0 0 0-1.762-.66c-.69-.124-1.38-.143-2.07-.143H6.254c-.74 0-1.48.02-2.19.145A4.895 4.895 0 0 0 2.3 1.233a5.083 5.083 0 0 0-1.75 2.95 8.581 8.581 0 0 0-.217 2.057c-.01.718 0 1.435 0 2.153v7.32c0 .718-.01 1.435 0 2.153a8.44 8.44 0 0 0 .217 2.043 5.083 5.083 0 0 0 1.755 2.942 4.906 4.906 0 0 0 1.762.657c.69.123 1.38.142 2.07.142h11.49c.74 0 1.48-.02 2.19-.145a4.896 4.896 0 0 0 1.762-.655 5.081 5.081 0 0 0 1.75-2.95 8.43 8.43 0 0 0 .217-2.043c.01-.718 0-1.435 0-2.153V8.277c0-.718.01-1.435 0-2.153zM12.19 17.82a3.398 3.398 0 1 1 0-6.797 3.398 3.398 0 0 1 0 6.797zm5.167-8.4a1.143 1.143 0 1 1 0-2.286 1.143 1.143 0 0 1 0 2.286zm-5.167 1.956a1.045 1.045 0 1 0 0 2.09 1.045 1.045 0 0 0 0-2.09z" />
    </svg>
  )
}

export default function AlbumCard({ album }) {
  const { pick_number, artist, album: title, year, artwork_url, spotify_url, apple_music_url, picker } = album

  return (
    <div
      className="album-card"
      onClick={() => window.open(spotify_url, '_blank', 'noopener,noreferrer')}
      role="link"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && window.open(spotify_url, '_blank', 'noopener,noreferrer')}
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
        <p className="album-card__meta">{year}</p>
        {picker && <span className="album-card__picker">{picker}</span>}
        <div className="album-card__links">
          {spotify_url && (
            <a
              className="album-card__platform-link album-card__platform-link--spotify"
              href={spotify_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open on Spotify"
              onClick={e => e.stopPropagation()}
            >
              <SpotifyIcon />
            </a>
          )}
          {apple_music_url && (
            <a
              className="album-card__platform-link album-card__platform-link--apple"
              href={apple_music_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open on Apple Music"
              onClick={e => e.stopPropagation()}
            >
              <AppleMusicIcon />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
