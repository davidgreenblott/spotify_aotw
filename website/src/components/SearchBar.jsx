export default function SearchBar({ value, onChange }) {
  return (
    <input
      className="search-bar"
      type="search"
      placeholder="Search artist or album..."
      value={value}
      onChange={e => onChange(e.target.value)}
    />
  )
}
