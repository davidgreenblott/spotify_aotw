import { useState, useEffect, useMemo } from 'react'
import { uniqueValues } from '../utils/filterSort'

export function useAlbums() {
  const [albums, setAlbums] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/data.json')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(data => {
        setAlbums(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load albums:', err)
        setError(err)
        setLoading(false)
      })
  }, [])

  return { albums, loading, error }
}

/** Derives sorted unique values for year, artist, and picker from an album list. */
export function useAlbumMetadata(albums) {
  return useMemo(() => ({
    years:   uniqueValues(albums, 'year'),
    artists: uniqueValues(albums, 'artist'),
    pickers: uniqueValues(albums, 'picker'),
  }), [albums])
}
