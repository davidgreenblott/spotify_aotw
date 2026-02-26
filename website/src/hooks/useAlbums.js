import { useState, useEffect } from 'react'

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
