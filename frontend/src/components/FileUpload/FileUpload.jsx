import React, { useState, useRef } from 'react';
import { Upload, CheckCircle, AlertCircle } from 'lucide-react';
import { TEXT } from '../../constants/text';
import { validateJSON } from '../../utils/jsonParser';
import styles from './FileUpload.module.css';

const FileUpload = ({ onFileUpload }) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null); // 'success', 'error', null
  const [uploadMessage, setUploadMessage] = useState('');
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (file) => {
    if (file.type !== 'application/json') {
      setUploadStatus('error');
      setUploadMessage('Please upload a JSON file');
      return;
    }

    try {
      const text = await file.text();
      const jsonData = JSON.parse(text);
      
      const validation = validateJSON(jsonData);
      if (!validation.isValid) {
        setUploadStatus('error');
        setUploadMessage(validation.error);
        return;
      }

      setUploadStatus('success');
      setUploadMessage(TEXT.FILE_UPLOAD.SUCCESS);
      onFileUpload(jsonData);
    } catch (error) {
      setUploadStatus('error');
      setUploadMessage(TEXT.FILE_UPLOAD.ERROR);
    }
  };

  const onButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Upload className={styles.icon} />
        <h3 className={styles.title}>{TEXT.FILE_UPLOAD.TITLE}</h3>
        <p className={styles.description}>{TEXT.FILE_UPLOAD.DESCRIPTION}</p>
      </div>

      <div
        className={`${styles.uploadArea} ${dragActive ? styles.dragActive : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleChange}
          className={styles.hiddenInput}
        />
        
        <div className={styles.uploadContent}>
          <Upload className={styles.uploadIcon} />
          <button
            onClick={onButtonClick}
            className={styles.uploadButton}
          >
            {TEXT.FILE_UPLOAD.BUTTON_TEXT}
          </button>
          <p className={styles.dragText}>{TEXT.FILE_UPLOAD.DRAG_TEXT}</p>
        </div>
      </div>

      {uploadStatus && (
        <div className={`${styles.status} ${styles[uploadStatus]}`}>
          {uploadStatus === 'success' ? (
            <CheckCircle className={styles.statusIcon} />
          ) : (
            <AlertCircle className={styles.statusIcon} />
          )}
          <span>{uploadMessage}</span>
        </div>
      )}
    </div>
  );
};

export default FileUpload;