import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles.css';

class AppErrorBoundary extends React.Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error('PDF Reader render failed:', error, info); }
  render() {
    if (this.state.error) {
      return <main style={{fontFamily:'system-ui',maxWidth:760,margin:'10vh auto',padding:24,border:'1px solid #e5a4a4',borderRadius:12,background:'#fff7f7',color:'#7f1d1d',whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>
        <h1 style={{fontSize:20}}>PDF Reader could not render</h1>
        <p>{String(this.state.error?.stack || this.state.error)}</p>
        <p>Copy this error and send it to the developer.</p>
      </main>;
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <AppErrorBoundary><App /></AppErrorBoundary>
);
