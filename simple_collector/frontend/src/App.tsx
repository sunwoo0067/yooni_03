import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import Collection from './pages/Collection'
import ExcelUpload from './pages/ExcelUpload'
import Settings from './pages/Settings'
import Bestseller from './pages/Bestseller'
import AISourcing from './pages/AISourcing'
import ImageManagement from './pages/ImageManagement'
import Scheduler from './pages/Scheduler'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/collection" element={<Collection />} />
          <Route path="/excel" element={<ExcelUpload />} />
          <Route path="/bestseller" element={<Bestseller />} />
          <Route path="/ai-sourcing" element={<AISourcing />} />
          <Route path="/images" element={<ImageManagement />} />
          <Route path="/scheduler" element={<Scheduler />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App