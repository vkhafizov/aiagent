import React from 'react';
import { MessageSquare, FileText, Hash, Clock } from 'lucide-react';
import { TEXT } from '../../constants/text';
import styles from './ContentDisplay.module.css';

const ContentDisplay = ({ content, format }) => {
  if (!content) {
    return (
      <div className={styles.noContent}>
        <FileText className={styles.noContentIcon} />
        <p className={styles.noContentText}>{TEXT.CONTENT_DISPLAY.NO_CONTENT}</p>
      </div>
    );
  }

  // Если есть HTML контент - отображаем его
  if (content?.content?.html) {
    return (
      <div className={styles.htmlContainer}>
        <div dangerouslySetInnerHTML={{ __html: content.content.html }} />
      </div>
    );
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderPosts = () => {
    if (!content.content?.posts) return null;

    return (
      <div className={styles.postsContainer}>
        <div className={styles.contentHeader}>
          <MessageSquare className={styles.headerIcon} />
          <h2 className={styles.contentTitle}>{TEXT.CONTENT_DISPLAY.POSTS_TITLE}</h2>
          <span className={styles.contentMeta}>
            {content.date} • {TEXT.DATE_SELECTOR.TIME_PERIODS[content.timePeriod]}
          </span>
        </div>
        
        <div className={styles.posts}>
          {content.content.posts.map((post, index) => (
            <div key={post.id || index} className={styles.post}>
              <div className={styles.postHeader}>
                <span className={styles.postNumber}>
                  {TEXT.CONTENT_DISPLAY.POST_PREFIX} {index + 1}
                </span>
                {post.timestamp && (
                  <div className={styles.postTime}>
                    <Clock className={styles.timeIcon} />
                    <span>{formatDate(post.timestamp)}</span>
                  </div>
                )}
              </div>
              
              {post.title && (
                <h3 className={styles.postTitle}>{post.title}</h3>
              )}
              
              <div className={styles.postContent}>
                {post.content}
              </div>
              
              {post.hashtags && post.hashtags.length > 0 && (
                <div className={styles.hashtags}>
                  <Hash className={styles.hashIcon} />
                  <div className={styles.hashtagList}>
                    {post.hashtags.map((tag, i) => (
                      <span key={i} className={styles.hashtag}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderArticle = () => {
    if (!content.content?.article) return null;

    const article = content.content.article;

    return (
      <div className={styles.articleContainer}>
        <div className={styles.contentHeader}>
          <FileText className={styles.headerIcon} />
          <h2 className={styles.contentTitle}>{TEXT.CONTENT_DISPLAY.ARTICLE_TITLE}</h2>
          <span className={styles.contentMeta}>
            {content.date} • {TEXT.DATE_SELECTOR.TIME_PERIODS[content.timePeriod]}
          </span>
        </div>
        
        <article className={styles.article}>
          {article.title && (
            <h1 className={styles.articleTitle}>{article.title}</h1>
          )}
          
          {article.summary && (
            <div className={styles.articleSummary}>
              <h3>Summary</h3>
              <p>{article.summary}</p>
            </div>
          )}
          
          <div className={styles.articleContent}>
            {article.content.split('\n\n').map((paragraph, index) => (
              <p key={index} className={styles.articleParagraph}>
                {paragraph}
              </p>
            ))}
          </div>
          
          {article.keyPoints && article.keyPoints.length > 0 && (
            <div className={styles.keyPoints}>
              <h3>Key Points</h3>
              <ul className={styles.keyPointsList}>
                {article.keyPoints.map((point, index) => (
                  <li key={index}>{point}</li>
                ))}
              </ul>
            </div>
          )}
          
          {article.hashtags && article.hashtags.length > 0 && (
            <div className={styles.hashtags}>
              <Hash className={styles.hashIcon} />
              <div className={styles.hashtagList}>
                {article.hashtags.map((tag, i) => (
                  <span key={i} className={styles.hashtag}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </article>
      </div>
    );
  };

  return (
    <div className={styles.container}>
      {format === 'posts' ? renderPosts() : renderArticle()}
    </div>
  );
};

export default ContentDisplay;