import React, { useState, useEffect } from 'react';
import { X, Settings as SettingsIcon, Info } from 'lucide-react';
import { TEXT } from '../../constants/text';
import styles from './Settings.module.css';

const Settings = ({ isOpen, onClose }) => {
  const [autoExportEnabled, setAutoExportEnabled] = useState(false);
  const [telegramChannel, setTelegramChannel] = useState('');
  const [exportSchedule, setExportSchedule] = useState('immediate');

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  const handleSave = () => {
    // Settings save functionality will be implemented later
    console.log('Settings saved:', {
      autoExportEnabled,
      telegramChannel,
      exportSchedule
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <div className={styles.titleSection}>
            <SettingsIcon className={styles.titleIcon} />
            <h2 className={styles.title}>{TEXT.SETTINGS.TITLE}</h2>
          </div>
          <button
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Close settings"
          >
            <X className={styles.closeIcon} />
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.comingSoonBanner}>
            <Info className={styles.bannerIcon} />
            <span>{TEXT.SETTINGS.COMING_SOON}</span>
          </div>

          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>
              {TEXT.SETTINGS.AUTO_EXPORT.TITLE}
            </h3>
            <p className={styles.sectionDescription}>
              {TEXT.SETTINGS.AUTO_EXPORT.DESCRIPTION}
            </p>

            <div className={styles.field}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={autoExportEnabled}
                  onChange={(e) => setAutoExportEnabled(e.target.checked)}
                  className={styles.checkbox}
                  disabled
                />
                <span className={styles.checkboxText}>
                  {TEXT.SETTINGS.AUTO_EXPORT.ENABLE}
                </span>
              </label>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>
                {TEXT.SETTINGS.AUTO_EXPORT.CHANNEL}
              </label>
              <input
                type="text"
                value={telegramChannel}
                onChange={(e) => setTelegramChannel(e.target.value)}
                placeholder={TEXT.SETTINGS.AUTO_EXPORT.CHANNEL_PLACEHOLDER}
                className={styles.input}
                disabled
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>
                {TEXT.SETTINGS.AUTO_EXPORT.SCHEDULE}
              </label>
              <select
                value={exportSchedule}
                onChange={(e) => setExportSchedule(e.target.value)}
                className={styles.select}
                disabled
              >
                {Object.entries(TEXT.SETTINGS.AUTO_EXPORT.SCHEDULES).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          <button
            className={styles.cancelButton}
            onClick={onClose}
          >
            {TEXT.GENERAL.CANCEL}
          </button>
          <button
            className={`${styles.saveButton} ${styles.disabled}`}
            onClick={handleSave}
            disabled
          >
            {TEXT.SETTINGS.SAVE_BUTTON}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;