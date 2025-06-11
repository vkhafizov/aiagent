// JSON Parser and Validation Utilities for Quantum Fusion GitHub Explainer

/**
 * Validates the structure of uploaded JSON content
 * @param {Object} jsonData - The parsed JSON data
 * @returns {Object} - Validation result with isValid boolean and error message
 */
export const validateJSON = (jsonData) => {
  try {
    // Check if jsonData is an object
    if (!jsonData || typeof jsonData !== 'object') {
      return {
        isValid: false,
        error: 'Invalid JSON format. Expected an object.'
      };
    }

    // Required top-level fields
    const requiredFields = ['format', 'date', 'timePeriod', 'content'];
    for (const field of requiredFields) {
      if (!(field in jsonData)) {
        return {
          isValid: false,
          error: `Missing required field: ${field}`
        };
      }
    }

    // Validate format
    if (!['posts', 'article'].includes(jsonData.format)) {
      return {
        isValid: false,
        error: 'Invalid format. Must be "posts" or "article".'
      };
    }

    // Validate date format (YYYY-MM-DD)
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(jsonData.date)) {
      return {
        isValid: false,
        error: 'Invalid date format. Expected YYYY-MM-DD.'
      };
    }

    // Validate time period
    if (!['24h', '7d', '30d'].includes(jsonData.timePeriod)) {
      return {
        isValid: false,
        error: 'Invalid time period. Must be "24h", "7d", or "30d".'
      };
    }

    // Validate content structure
    if (!jsonData.content || typeof jsonData.content !== 'object') {
      return {
        isValid: false,
        error: 'Invalid content structure. Expected an object.'
      };
    }

    // Validate content based on format
    if (jsonData.format === 'posts') {
      const postsValidation = validatePostsContent(jsonData.content);
      if (!postsValidation.isValid) {
        return postsValidation;
      }
    } else if (jsonData.format === 'article') {
      const articleValidation = validateArticleContent(jsonData.content);
      if (!articleValidation.isValid) {
        return articleValidation;
      }
    }

    return {
      isValid: true,
      error: null
    };

  } catch (error) {
    return {
      isValid: false,
      error: `JSON validation error: ${error.message}`
    };
  }
};

/**
 * Validates posts content structure
 * @param {Object} content - The content object
 * @returns {Object} - Validation result
 */
const validatePostsContent = (content) => {
  if (!content.posts || !Array.isArray(content.posts)) {
    return {
      isValid: false,
      error: 'Posts format requires a "posts" array in content.'
    };
  }

  if (content.posts.length === 0) {
    return {
      isValid: false,
      error: 'Posts array cannot be empty.'
    };
  }

  // Validate each post
  for (let i = 0; i < content.posts.length; i++) {
    const post = content.posts[i];
    
    if (!post || typeof post !== 'object') {
      return {
        isValid: false,
        error: `Post ${i + 1} is not a valid object.`
      };
    }

    // Required post fields
    if (!post.content || typeof post.content !== 'string') {
      return {
        isValid: false,
        error: `Post ${i + 1} missing required "content" field.`
      };
    }

    // Optional fields validation
    if (post.title && typeof post.title !== 'string') {
      return {
        isValid: false,
        error: `Post ${i + 1} title must be a string.`
      };
    }

    if (post.hashtags && !Array.isArray(post.hashtags)) {
      return {
        isValid: false,
        error: `Post ${i + 1} hashtags must be an array.`
      };
    }

    if (post.timestamp && !isValidTimestamp(post.timestamp)) {
      return {
        isValid: false,
        error: `Post ${i + 1} has invalid timestamp format.`
      };
    }
  }

  return { isValid: true, error: null };
};

/**
 * Validates article content structure
 * @param {Object} content - The content object
 * @returns {Object} - Validation result
 */
const validateArticleContent = (content) => {
  if (!content.article || typeof content.article !== 'object') {
    return {
      isValid: false,
      error: 'Article format requires an "article" object in content.'
    };
  }

  const article = content.article;

  // Required article fields
  if (!article.content || typeof article.content !== 'string') {
    return {
      isValid: false,
      error: 'Article missing required "content" field.'
    };
  }

  // Optional fields validation
  if (article.title && typeof article.title !== 'string') {
    return {
      isValid: false,
      error: 'Article title must be a string.'
    };
  }

  if (article.summary && typeof article.summary !== 'string') {
    return {
      isValid: false,
      error: 'Article summary must be a string.'
    };
  }

  if (article.keyPoints && !Array.isArray(article.keyPoints)) {
    return {
      isValid: false,
      error: 'Article keyPoints must be an array.'
    };
  }

  if (article.hashtags && !Array.isArray(article.hashtags)) {
    return {
      isValid: false,
      error: 'Article hashtags must be an array.'
    };
  }

  return { isValid: true, error: null };
};

/**
 * Validates timestamp format (ISO 8601)
 * @param {string} timestamp - The timestamp to validate
 * @returns {boolean} - Whether the timestamp is valid
 */
const isValidTimestamp = (timestamp) => {
  if (typeof timestamp !== 'string') return false;
  
  try {
    const date = new Date(timestamp);
    return date instanceof Date && !isNaN(date.getTime());
  } catch {
    return false;
  }
};

/**
 * Sanitizes and formats content for display
 * @param {Object} content - The content to sanitize
 * @returns {Object} - Sanitized content
 */
export const sanitizeContent = (content) => {
  if (!content) return null;

  // Create a deep copy to avoid mutating original data
  const sanitized = JSON.parse(JSON.stringify(content));

  if (sanitized.content?.posts) {
    sanitized.content.posts = sanitized.content.posts.map(post => ({
      ...post,
      content: sanitizeText(post.content),
      title: post.title ? sanitizeText(post.title) : undefined,
      hashtags: post.hashtags ? post.hashtags.map(tag => sanitizeHashtag(tag)) : undefined
    }));
  }

  if (sanitized.content?.article) {
    const article = sanitized.content.article;
    sanitized.content.article = {
      ...article,
      content: sanitizeText(article.content),
      title: article.title ? sanitizeText(article.title) : undefined,
      summary: article.summary ? sanitizeText(article.summary) : undefined,
      keyPoints: article.keyPoints ? article.keyPoints.map(point => sanitizeText(point)) : undefined,
      hashtags: article.hashtags ? article.hashtags.map(tag => sanitizeHashtag(tag)) : undefined
    };
  }

  return sanitized;
};

/**
 * Sanitizes text content
 * @param {string} text - Text to sanitize
 * @returns {string} - Sanitized text
 */
const sanitizeText = (text) => {
  if (typeof text !== 'string') return '';
  
  // Remove potential HTML tags and normalize whitespace
  return text
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .replace(/\s+/g, ' ') // Normalize whitespace
    .trim();
};

/**
 * Sanitizes hashtag format
 * @param {string} hashtag - Hashtag to sanitize
 * @returns {string} - Sanitized hashtag
 */
const sanitizeHashtag = (hashtag) => {
  if (typeof hashtag !== 'string') return '';
  
  // Ensure hashtag starts with # and contains only valid characters
  let cleaned = hashtag.trim().replace(/[^a-zA-Z0-9_]/g, '');
  if (cleaned && !cleaned.startsWith('#')) {
    cleaned = '#' + cleaned;
  }
  
  return cleaned || '#QuantumFusion';
};

/**
 * Generates sample JSON for testing
 * @param {string} format - 'posts' or 'article'
 * @returns {Object} - Sample JSON data
 */
export const generateSampleJSON = (format = 'posts') => {
  const baseData = {
    format,
    date: new Date().toISOString().split('T')[0],
    timePeriod: '24h',
    content: {}
  };

  if (format === 'posts') {
    baseData.content.posts = [
      {
        id: 1,
        title: "Quantum Fusion Makes Major Breakthrough",
        content: "Today, the Quantum Fusion team successfully implemented a revolutionary consensus mechanism that increases transaction throughput by 300%. This breakthrough represents months of dedicated research and development.",
        timestamp: new Date().toISOString(),
        hashtags: ["#QuantumFusion", "#Blockchain", "#Innovation", "#DeFi"]
      },
      {
        id: 2,
        title: "New Smart Contract Features Released",
        content: "Our latest update includes enhanced smart contract capabilities with improved gas optimization and cross-chain compatibility. Developers can now build more efficient dApps on our platform.",
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        hashtags: ["#SmartContracts", "#Web3", "#Development", "#QuantumFusion"]
      }
    ];
  } else {
    baseData.content.article = {
      title: "Quantum Fusion's Revolutionary Day: Major Updates and Breakthroughs",
      summary: "Today marked a significant milestone for Quantum Fusion with multiple breakthrough achievements in blockchain technology, smart contract optimization, and community growth.",
      content: "The Quantum Fusion development team has achieved remarkable progress in the past 24 hours, implementing groundbreaking solutions that will reshape the blockchain landscape.\n\nOur primary achievement involves the successful deployment of a novel consensus mechanism that dramatically improves network efficiency. Through innovative algorithmic approaches, we've managed to increase transaction throughput by an impressive 300% while maintaining the highest security standards.\n\nAdditionally, our smart contract platform has received significant upgrades, featuring enhanced gas optimization protocols and seamless cross-chain compatibility. These improvements enable developers to create more sophisticated and efficient decentralized applications.\n\nThe community response has been overwhelmingly positive, with increased participation in our governance protocols and growing adoption of our DeFi solutions.",
      keyPoints: [
        "300% increase in transaction throughput through new consensus mechanism",
        "Enhanced smart contract capabilities with gas optimization",
        "Improved cross-chain compatibility for better interoperability",
        "Strong community engagement and governance participation",
        "Continued focus on security and decentralization principles"
      ],
      hashtags: ["#QuantumFusion", "#Blockchain", "#DeFi", "#Innovation", "#Web3"]
    };
  }

  return baseData;
};