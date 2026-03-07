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
      <path d="M15.2 4.4a1 1 0 0 0-.4 0L9 5.7a1 1 0 0 0-.8 1v7.9a3 3 0 0 0-1-.2c-1.7 0-3 .9-3 2.4S5.5 19 7.1 19c1.9 0 3.1-1.1 3.1-2.7V8l4.9-1.1v5.7a3 3 0 0 0-1-.2c-1.7 0-3 .9-3 2.4S12.4 17 14 17c1.9 0 3.1-1.1 3.1-2.7V5.3a.94.94 0 0 0-.4-.7.96.96 0 0 0-.6-.2z" />
    </svg>
  )
}

function SoundCloudIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M1.5 14.5c0 1.4 1.1 2.5 2.5 2.5h13.5c1.9 0 3.5-1.6 3.5-3.5 0-1.7-1.2-3.1-2.8-3.4.1-.4.1-.7.1-1.1C18.3 7 16.3 5 13.8 5c-1.3 0-2.5.5-3.3 1.4C9.9 5.5 8.8 5 7.5 5 5 5 3 7 3 9.5c0 .3 0 .6.1.9C2.1 11 1.5 12.7 1.5 14.5zm4.2-3.3.8.1V10c0-.7.6-1.2 1.2-1.2s1.2.5 1.2 1.2v4.7H5.7c-.7 0-1.2-.6-1.2-1.2 0-.7.5-1.2 1.2-1.3zm3.8-1.9V15H10v-5.7c0-.4.3-.7.7-.7s.7.3.7.7V15h.6V8.8c0-.4.3-.7.7-.7s.7.3.7.7V15h.6V9.5c0-.4.3-.7.7-.7s.7.3.7.7V15h.3c.7 0 1.2.6 1.2 1.2H9.5V9.3z"/>
    </svg>
  )
}

export default function AlbumCard({ album }) {
  const { pick_number, artist, album: title, year, artwork_url, spotify_url, apple_music_url, alt_url, picker } = album
  const primaryUrl = spotify_url || alt_url

  return (
    <div
      className="album-card"
      onClick={() => window.open(primaryUrl, '_blank', 'noopener,noreferrer')}
      role="link"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && window.open(primaryUrl, '_blank', 'noopener,noreferrer')}
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
          {alt_url && !spotify_url && (
            <a
              className="album-card__platform-link album-card__platform-link--soundcloud"
              href={alt_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open on SoundCloud"
              onClick={e => e.stopPropagation()}
            >
              <SoundCloudIcon />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
