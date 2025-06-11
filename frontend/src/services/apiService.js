// frontend/src/services/apiService.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      console.log(`API Request: ${config.method || 'GET'} ${url}`);
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log(`API Response:`, data);
      return data;
    } catch (error) {
      console.error(`API request failed:`, error);
      throw error;
    }
  }

  // Health check
  async healthCheck() {
    return this.request('/health');
  }

  // Generate posts for frontend (NEW ENDPOINT)
  async generatePosts(repository, timePeriod, format = 'posts') {
    return this.request('/api/generate-posts', {
      method: 'POST',
      body: JSON.stringify({
        repository,
        time_period: timePeriod,
        format
      }),
    });
  }

  // Get existing posts data
  async getPostsData(timePeriod) {
    return this.request(`/api/posts-data/${timePeriod}`);
  }

  // Original endpoints (still available)
  async generatePost(repository, timePeriod) {
    return this.request('/generate-post', {
      method: 'POST',
      body: JSON.stringify({
        repository,
        time_period: timePeriod,
        target_audience: 'general'
      }),
    });
  }

  async listPosts(timePeriod) {
    return this.request(`/posts/${timePeriod}`);
  }

  async collectCommits(repository, hours = 2) {
    return this.request(`/collect-commits/${repository}?hours=${hours}`, {
      method: 'POST'
    });
  }
}

export default new ApiService();