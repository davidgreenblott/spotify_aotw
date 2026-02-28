import { BrowserRouter, Routes, Route, Link, NavLink } from 'react-router-dom'
import PicksPage from './pages/PicksPage'
import AboutPage from './pages/AboutPage'
import AnalyticsPage from './pages/AnalyticsPage'
import './index.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="header">
          <div className="header-top">
            <Link to="/" className="site-title">
              <h1>album of the week</h1>
            </Link>
            <nav className="nav">
              <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                the picks
              </NavLink>
              <NavLink to="/analytics" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                analytics
              </NavLink>
              <NavLink to="/about" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                about
              </NavLink>
            </nav>
          </div>
        </header>
        <Routes>
          <Route path="/" element={<PicksPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
