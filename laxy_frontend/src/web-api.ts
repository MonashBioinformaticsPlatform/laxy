declare function require(path: string): any;

import 'es6-promise';
import axios, {AxiosResponse} from 'axios';
const Cookies = require('js-cookie');

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

    public static getAuthHeader() {
        const token = sessionStorage.getItem('accessToken');
        return {Authorization: `Bearer ${token}`};
    }

    public static getCsrfToken(): string {
        return Cookies.get('csrftoken');
    }
}
