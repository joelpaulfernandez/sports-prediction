import axios from 'axios';

// Single shared axios instance. Add interceptors here once (auth, retry, 401 handling).
const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

export default http;
