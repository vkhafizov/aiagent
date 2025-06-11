import React from 'react';
import { FileText, MessageSquare } from 'lucide-react';
import { TEXT } from '../../constants/text';
import styles from './FormatSelector.module.css';

const FormatSelector = ({ selectedFormat, onFormatChange }) => {
  const formats = [
    {
      id: 'posts',
      icon: MessageSquare,
      ...TEXT.FORMAT_SELECTOR.FORMATS.posts
    },
    {
      id: 'article',
      icon: FileText,
      ...TEXT.FORMAT_SELECTOR.FORMATS.article
    }
  ];

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>{TEXT.FORMAT_SELECTOR.TITLE}</h3>
        <p className={styles.description}>{TEXT.FORMAT_SELECTOR.DESCRIPTION}</p>
      </div>
      
      <div className={styles.options}>
        {formats.map((format) => {
          const IconComponent = format.icon;
          return (
            <button
              key={format.id}
              className={`${styles.option} ${selectedFormat === format.id ? styles.selected : ''}`}
              onClick={() => onFormatChange(format.id)}
            >
              <IconComponent className={styles.optionIcon} />
              <div className={styles.optionContent}>
                <h4 className={styles.optionTitle}>{format.title}</h4>
                <p className={styles.optionDescription}>{format.description}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default FormatSelector;