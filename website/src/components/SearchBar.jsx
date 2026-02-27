import { useState, useEffect } from 'react'
import './SearchBar.css'

export default function SearchBar({ value, onChange, placeholder = 'Search albums, artists...' }) {
  const [localValue, setLocalValue] = useState(value)

  // Debounce: wait 300ms after last keystroke before calling onChange
  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(localValue)
    }, 300)
    return () => clearTimeout(timer)
  }, [localValue, onChange])

  const handleClear = () => {
    setLocalValue('')
    onChange('')
  }

  return (
    <div className="search-bar">
      <input
        type="text"
        value={localValue}
        onChange={e => setLocalValue(e.target.value)}
        placeholder={placeholder}
        className="search-input"
      />
      {localValue && (
        <button className="clear-button" onClick={handleClear} aria-label="Clear search">
          ✕
        </button>
      )}
    </div>
  )
}
