import React from 'react';
import { TEXT } from '../../constants/text';
import styles from './Header.module.css';

const Header = () => {
  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>QF</div>
          <div className={styles.logoText}>
            <h1 className={styles.title}>{TEXT.HEADER.TITLE}</h1>
            <p className={styles.tagline}>{TEXT.HEADER.TAGLINE}</p>
          </div>
        </div>
        <p className={styles.subtitle}>{TEXT.HEADER.SUBTITLE}</p>
      </div>
    </header>
  );
};

export default Header;