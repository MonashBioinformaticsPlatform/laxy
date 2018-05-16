declare function require(path: string): any;

import 'es6-promise';
import axios, {AxiosResponse} from 'axios';
const Cookies = require('js-cookie');

class NotImplementedError extends Error {
  constructor(message: string) {
    super(message);
  }
}

export class WebAPI {
    private static baseUrl: string = 'http://118.138.240.175:8001';
    // private static baseUrl: string = 'http://localhost:8001';
    public static fetcher = axios.create({
        baseURL: WebAPI.baseUrl,
        withCredentials: true,
        xsrfHeaderName: 'X-CSRFToken',
        xsrfCookieName: 'csrftoken'});

    public static async getAuthToken(user: string, pass: string): Promise<string> {
        try {
            const response = await this.fetcher.post(`/api/v1/auth/get-token/`,
                {username: user, password: pass}) as AxiosResponse;
            sessionStorage.setItem('accessToken', response.data.token);
            return response.data.token;
        } catch (error) {
            throw error;
        }
    }

    public static async login(user: string, pass: string) {
        try {
            return await this.fetcher.post(`/api/v1/auth/login/`,
                {username: user, password: pass}) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async logout() {
        try {
            return await this.fetcher.get(`/api/v1/auth/logout/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async isLoggedIn() {
        try {
            const result = await this.fetcher.get(`/accounts/profile/`) as AxiosResponse;
            return true;
        } catch (error) {
            return false;
        }
    }

    public static async getUserProfile() {
        try {
            return await this.fetcher.get(`/accounts/profile/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static getAuthHeader() {
        const token = sessionStorage.getItem('accessToken');
        return {Authorization: `Bearer ${token}`};
    }

    public static getCsrfToken(): string {
        return Cookies.get('csrftoken');
    }

    public static async getJobs(page: number, page_size: number) {
        try {
            return await this.fetcher.get(
                `/api/v1/jobs/?page=${page}&page_size=${page_size}`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getJob(job_id: string) {
        try {
            return await this.fetcher.get(
                `/api/v1/job/${job_id}/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async cancelJob(id: string) {
        try {
            return await this.fetcher.patch(
                `/api/v1/job/${id}/`,
                {status: 'cancelled'}) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getFileSet(fileset_id: string) {
        try {
            return await this.fetcher.get(
                `/api/v1/fileset/${fileset_id}/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }
}
