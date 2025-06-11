import React from 'react';
import { Send, Settings, Info } from 'lucide-react';
import { TEXT } from '../../constants/text';
import styles from './ExportControls.module.css';

const ExportControls = ({ onExport, onSettingsToggle }) => {
  return (
    <div className={styles.container}>
      <h3 className={styles.title}>{TEXT.EXPORT.TITLE}</h3>
      
      <div className={styles.controls}>
        <div className={styles.exportButton}>
          <button
            className={`${styles.telegramButton} ${styles.disabled}`}
            disabled
            title={TEXT.EXPORT.TELEGRAM_DISABLED}
          >
            <Send className={styles.buttonIcon} />
            {TEXT.EXPORT.TELEGRAM_BUTTON}
          </button>
          
          <div className={styles.comingSoon}>
            <Info className={styles.infoIcon} />
            <span>{TEXT.EXPORT.TELEGRAM_DISABLED}</span>
          </div>
        </div>
        
        <button
          className={styles.settingsButton}
          onClick={onSettingsToggle}
        >
          <Settings className={styles.buttonIcon} />
          {TEXT.SETTINGS.TITLE}
        </button>
      </div>
    </div>
  );
};

export default ExportControls;