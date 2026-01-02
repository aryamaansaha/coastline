import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { AuthProvider } from './context/AuthContext.tsx'
import { TripProvider } from './context/TripContext.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <TripProvider>
        <App />
      </TripProvider>
    </AuthProvider>
  </React.StrictMode>,
)
