import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { sendFrontendLog } from './services/api'

window.addEventListener('error', (event) => {
  sendFrontendLog({
    level: 'error',
    message: 'ui_error',
    details: {
      message: event.message,
      source: event.filename,
      line: event.lineno,
      col: event.colno,
    },
  });
});

window.addEventListener('unhandledrejection', (event) => {
  sendFrontendLog({
    level: 'error',
    message: 'promise_rejection',
    details: {
      reason: String(event.reason || 'unknown'),
    },
  });
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
