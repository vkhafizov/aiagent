import React, { useState, useEffect } from 'react';
import './App.css';
import { TEXT } from './constants/text';
import Header from './components/Header/Header';
import DateSelector from './components/DateSelector/DateSelector';
import FormatSelector from './components/FormatSelector/FormatSelector';
import FileUpload from './components/FileUpload/FileUpload';
import ContentDisplay from './components/ContentDisplay/ContentDisplay';
import ExportControls from './components/ExportControls/ExportControls';
import Settings from './components/Settings/Settings';
import apiService from './services/apiService';

function App() {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedTimePeriod, setSelectedTimePeriod] = useState('24h');
  const [selectedFormat, setSelectedFormat] = useState('posts');
  const [uploadedContent, setUploadedContent] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  
  // NEW STATES FOR BACKEND CONNECTION
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [generateButtonText, setGenerateButtonText] = useState('Generate Posts');

  // Check backend connection on startup
  useEffect(() => {
    checkBackendHealth();
  }, []);

  // Auto-generate posts when time period changes (for demo)
  useEffect(() => {
    if (backendStatus === 'connected') {
      generatePosts();
    }
  }, [selectedTimePeriod, backendStatus]);

  const checkBackendHealth = async () => {
    try {
      setBackendStatus('checking');
      const health = await apiService.healthCheck();
      console.log('Backend health:', health);
      setBackendStatus('connected');
      setError(null);
    } catch (error) {
      console.error('Backend health check failed:', error);
      setBackendStatus('disconnected');
      setError(`Backend connection failed: ${error.message}`);
    }
  };

  const generatePosts = async () => {
    if (backendStatus !== 'connected') {
      setError('Backend is not connected. Please check your backend server.');
      return;
    }

    setLoading(true);
    setError(null);
    setGenerateButtonText('Generating...');

    try {
      console.log(`Generating posts for ${selectedTimePeriod} period...`);
      
      const response = await apiService.generatePosts(
        'QuantumFusion-network/qf-polkavm-sdk', 
        selectedTimePeriod,
        selectedFormat
      );

      console.log('Backend response:', response);

      if (response.success) {
        // Format the response for ContentDisplay component
        const formattedContent = {
          format: selectedFormat,
          date: selectedDate,
          timePeriod: selectedTimePeriod,
          content: {
            posts: response.posts.map(post => ({
              id: post.id,
              title: post.title,
              content: post.content,
              hashtags: post.hashtags,
              timestamp: post.timestamp,
              type: post.type
            }))
          },
          metadata: response.metadata
        };

        setUploadedContent(formattedContent);
        setGenerateButtonText(`✅ Generated ${response.posts.length} posts`);
        
        // Reset button text after 3 seconds
        setTimeout(() => {
          setGenerateButtonText('Generate Posts');
        }, 3000);

      } else {
        setError(response.error_message || 'Failed to generate posts');
        setGenerateButtonText('❌ Generation failed');
        setTimeout(() => {
          setGenerateButtonText('Generate Posts');
        }, 3000);
      }

    } catch (error) {
      console.error('Error generating posts:', error);
      setError(`Error: ${error.message}`);
      setGenerateButtonText('❌ Generation failed');
      setTimeout(() => {
        setGenerateButtonText('Generate Posts');
      }, 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (date, timePeriod) => {
    setSelectedDate(date);
    setSelectedTimePeriod(timePeriod);
  };

  const handleFormatChange = async (format) => {
    setSelectedFormat(format);
    
    // If we have backend connection, regenerate posts in new format
    if (backendStatus === 'connected') {
      generatePosts();
    }
  };

  const handleFileUpload = (content) => {
    setUploadedContent(content);
  };

  const handleExport = () => {
    console.log('Export to Telegram requested');
    // TODO: Implement export functionality
  };

  const handleSettingsToggle = () => {
    setShowSettings(!showSettings);
  };

  const getStatusColor = () => {
    switch (backendStatus) {
      case 'connected': return '#4caf50';
      case 'disconnected': return '#f44336';
      case 'checking': return '#ff9800';
      default: return '#9e9e9e';
    }
  };

  const getStatusText = () => {
    switch (backendStatus) {
      case 'connected': return 'Backend Connected';
      case 'disconnected': return 'Backend Disconnected';
      case 'checking': return 'Checking Backend...';
      default: return 'Unknown Status';
    }
  };

  return (
    <div className="app">
      <Header />
      
      {/* BACKEND STATUS INDICATOR */}
      <div style={{
        padding: '10px',
        background: getStatusColor(),
        color: 'white',
        textAlign: 'center',
        fontSize: '14px',
        fontWeight: 'bold'
      }}>
        🔗 {getStatusText()}
        {backendStatus === 'disconnected' && (
          <button 
            onClick={checkBackendHealth}
            style={{
              marginLeft: '10px',
              background: 'rgba(255,255,255,0.3)',
              border: 'none',
              color: 'white',
              padding: '5px 10px',
              borderRadius: '3px',
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
        )}
      </div>

      <main className="main-content">
        <div className="controls-section">
          <DateSelector
            selectedDate={selectedDate}
            selectedTimePeriod={selectedTimePeriod}
            onDateChange={handleDateChange}
            onGenerate={generatePosts}
            loading={loading}
            backendStatus={backendStatus}
            generateButtonText={generateButtonText}
          />
          
          <FormatSelector
            selectedFormat={selectedFormat}
            onFormatChange={handleFormatChange}
          />
          
          <ExportControls
            onExport={handleExport}
            onSettingsToggle={handleSettingsToggle}
          />
        </div>

        <div className="content-section">
          {/* ERROR DISPLAY */}
          {error && (
            <div style={{
              background: '#ffebee',
              color: '#c62828',
              padding: '15px',
              borderRadius: '5px',
              marginBottom: '20px',
              border: '1px solid #ffcdd2'
            }}>
              ❌ {error}
            </div>
          )}

          {/* LOADING INDICATOR */}
          {loading && (
            <div style={{
              background: '#e3f2fd',
              color: '#1976d2',
              padding: '15px',
              borderRadius: '5px',
              marginBottom: '20px',
              textAlign: 'center'
            }}>
              ⏳ Generating posts... This may take 10-30 seconds.
            </div>
          )}

          <ContentDisplay
            content={uploadedContent}
            format={selectedFormat}
          />
        </div>

        <div className="export-section">
          {/* Removed FileUpload since we're using backend now */}
        </div>
      </main>

      {showSettings && (
        <Settings
          isOpen={showSettings}
          onClose={() => setShowSettings(false)}
        />
      )}

      <footer className="footer">
        <p>{TEXT.BRANDING.FOOTER_TEXT}</p>
        <p style={{ fontSize: '12px', color: '#666' }}>
          Backend: {backendStatus === 'connected' ? '✅' : '❌'} | 
          API: http://localhost:8000 | 
          Posts: {uploadedContent?.content?.posts?.length || 0}
        </p>
      </footer>
    </div>
  );
}

export default App;