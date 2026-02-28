import { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { useAlbums } from '../hooks/useAlbums'
import { uniqueDecades } from '../utils/filterSort'
import './AnalyticsPage.css'

export default function AnalyticsPage() {
  const { albums, loading, error } = useAlbums()

  const decadeData = useMemo(() => {
    if (!albums.length) return []
    return uniqueDecades(albums)
      .map(decade => ({
        decade: `${decade}s`,
        count: albums.filter(a => Math.floor(Number(a.year) / 10) * 10 === decade).length,
      }))
      .sort((a, b) => a.decade.localeCompare(b.decade))
  }, [albums])

  if (loading) return <div className="status">Loading...</div>
  if (error)   return <div className="status error">Failed to load albums.</div>

  return (
    <main className="analytics-page">
      <h2>analytics</h2>

      <section className="chart-section">
        <h3>picks by release decade</h3>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={decadeData} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid vertical={false} stroke="#333" />
              <XAxis dataKey="decade" tick={{ fill: '#a0a0a0', fontSize: 13 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#a0a0a0', fontSize: 13 }} axisLine={false} tickLine={false} width={32} />
              <Tooltip
                cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                contentStyle={{ background: '#1e1e1e', border: '1px solid #333', borderRadius: 8 }}
                labelStyle={{ color: '#e5e5e5', fontWeight: 600 }}
                itemStyle={{ color: '#1db954' }}
                formatter={(value) => [value, 'picks']}
              />
              <Bar dataKey="count" fill="#1db954" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </main>
  )
}
