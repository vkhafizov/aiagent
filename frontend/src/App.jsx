import React, { useState } from 'react';
import './App.css';
import { TEXT } from './constants/text';
import Header from './components/Header/Header';
import DateSelector from './components/DateSelector/DateSelector';
import FormatSelector from './components/FormatSelector/FormatSelector';
import FileUpload from './components/FileUpload/FileUpload';
import ContentDisplay from './components/ContentDisplay/ContentDisplay';
import ExportControls from './components/ExportControls/ExportControls';
import Settings from './components/Settings/Settings';

function App() {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedTimePeriod, setSelectedTimePeriod] = useState('24h');
  const [selectedFormat, setSelectedFormat] = useState('posts');
  const [uploadedContent, setUploadedContent] = useState(null);
  const [showSettings, setShowSettings] = useState(false);

  const handleDateChange = (date, timePeriod) => {
    setSelectedDate(date);
    setSelectedTimePeriod(timePeriod);
  };

  const handleFormatChange = async (format) => {
    setSelectedFormat(format);
    
    // Попытка загрузить соответствующий HTML файл
    try {
      const fileName = format === 'posts' ? 'posts.html' : 'article.html';
      const response = await fetch(`/data/${fileName}`);
      
      if (response.ok) {
        const htmlContent = await response.text();
        setUploadedContent({
          format: format,
          date: selectedDate,
          timePeriod: selectedTimePeriod,
          content: {
            html: htmlContent
          }
        });
        console.log(`Автоматически загружен файл: ${fileName}`);
      } else {
        console.log(`Файл ${fileName} не найден в public/data/`);
      }
    } catch (error) {
      console.log(`Ошибка при загрузке файла: ${error.message}`);
    }
  };

  const handleFileUpload = (content) => {
    setUploadedContent(content);
  };

  const handleExport = () => {
    // Export functionality will be implemented later
    console.log('Export to Telegram requested');
  };

  const handleSettingsToggle = () => {
    setShowSettings(!showSettings);
  };

  return (
    <div className="app">
      <Header />
      
      <main className="main-content">
        <div className="controls-section">
          <DateSelector
            selectedDate={selectedDate}
            selectedTimePeriod={selectedTimePeriod}
            onDateChange={handleDateChange}
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
          <ContentDisplay
            content={uploadedContent}
            format={selectedFormat}
          />
        </div>

        <div className="export-section">
         {/* <FileUpload onFileUpload={handleFileUpload} />  */}
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
      </footer>
    </div>
  );
}

export default App;