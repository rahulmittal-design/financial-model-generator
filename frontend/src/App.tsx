import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import ProjectDetail from './pages/ProjectDetail'
import DocumentReview from './pages/DocumentReview'
import MappingReview from './pages/MappingReview'
import ModelBuilder from './pages/ModelBuilder'
import ForecastView from './pages/ForecastView'
import ChatAssistant from './pages/ChatAssistant'
import LLMSetup from './pages/LLMSetup'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/projects/:projectId/documents/:docId" element={<DocumentReview />} />
          <Route path="/projects/:projectId/mapping" element={<MappingReview />} />
          <Route path="/projects/:projectId/model" element={<ModelBuilder />} />
          <Route path="/projects/:projectId/forecast" element={<ForecastView />} />
          <Route path="/projects/:projectId/chat" element={<ChatAssistant />} />
          <Route path="/llm-setup" element={<LLMSetup />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
