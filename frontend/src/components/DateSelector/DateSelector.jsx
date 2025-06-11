import React from 'react';
import { Calendar } from 'lucide-react';
import { TEXT } from '../../constants/text';
import styles from './DateSelector.module.css';

const DateSelector = ({ 
  selectedDate, 
  selectedTimePeriod, 
  onDateChange, 
  onGenerate, 
  loading, 
  backendStatus, 
  generateButtonText 
}) => {
  const handleDateChange = (e) => {
    onDateChange(e.target.value, selectedTimePeriod);
  };

  const handleTimePeriodChange = (e) => {
    onDateChange(selectedDate, e.target.value);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Calendar className={styles.icon} />
        <h3 className={styles.title}>{TEXT.DATE_SELECTOR.TITLE}</h3>
      </div>
      
      <div className={styles.controls}>
        <div className={styles.field}>
          <label className={styles.label}>
            {TEXT.DATE_SELECTOR.DATE_LABEL}
          </label>
          <input
            type="date"
            value={selectedDate}
            onChange={handleDateChange}
            className={styles.dateInput}
          />
        </div>
        
        <div className={styles.field}>
          <label className={styles.label}>
            {TEXT.DATE_SELECTOR.TIME_PERIOD_LABEL}
          </label>
          <select
            value={selectedTimePeriod}
            onChange={handleTimePeriodChange}
            className={styles.select}
          >
            {Object.entries(TEXT.DATE_SELECTOR.TIME_PERIODS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* GENERATE BUTTON MOVED HERE */}
        <div className={styles.field}>
          <button
            onClick={onGenerate}
            disabled={loading || backendStatus !== 'connected'}
            className={`${styles.generateButton} ${loading ? styles.loading : ''} ${backendStatus !== 'connected' ? styles.disabled : ''}`}
          >
            {loading ? '⏳ ' + generateButtonText : '🚀 ' + generateButtonText}
          </button>
          <p className={styles.repositoryInfo}>
            Repository: QuantumFusion-network/qf-polkavm-sdk
          </p>
        </div>
      </div>
    </div>
  );
};

export default DateSelector;