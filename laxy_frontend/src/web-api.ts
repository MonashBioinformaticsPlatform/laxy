import 'es6-promise';
import axios, {AxiosResponse, AxiosRequestConfig} from 'axios';

import * as Cookies from 'js-cookie';
import {getDomain} from 'tldjs';

import {browserLocale} from './util';
import * as moment from 'moment';

moment.locale(browserLocale());

export class WebAPI {

    public static apiSettings = {
        url: process.env.LAXY_FRONTEND_API_URL || 'http://localhost:8001',
        frontendUrl: process.env.LAXY_FRONTEND_URL || 'http://localhost:8002',
    };

    public static get baseUrl(): string {
        return WebAPI.apiSettings.url;
    }

    /* Axios has this silly quirk where the Content-Type header is removed
       unless you have 'data'. So we add empty data.
     */
    public static axiosConfig: AxiosRequestConfig = {
        baseURL: WebAPI.baseUrl,
        withCredentials: true,
        xsrfHeaderName: 'X-CSRFToken',
        xsrfCookieName: 'csrftoken',
        headers: {'Content-Type': 'application/json'},
        data: {},
        params: {},
    };

    public static fetcher = axios.create(WebAPI.axiosConfig);

    /*
     * Token authentication is currently not in use - session authentication via
     *  cookies is preferred due to less opportunities for XSS vulnerabilities.

    public static readonly authTokenName = 'accessToken';

    public static storeAccessToken(token: string) {
        // sessionStorage.setItem(WebAPI.authTokenName, token);
        localStorage.setItem(WebAPI.authTokenName, token);
    }

    public static get accessToken() {
        return localStorage.getItem(WebAPI.authTokenName);
    }

    public static getAuthHeader() {
        const token = WebAPI.accessToken;
        return {Authorization: `Bearer ${token}`};
    }

    public static async getAuthToken(user: string, pass: string): Promise<string> {
        try {
            const response = await this.fetcher.post(`/api/v1/auth/get-token/`,
                {username: user, password: pass}) as AxiosResponse;
            WebAPI.storeAccessToken(response.data.token);
            return response.data.token;
        } catch (error) {
            throw error;
        }
    }
    */

    public static setQueryParamAccessToken(access_token: string) {
        WebAPI.axiosConfig.params.access_token = access_token;
    }

    public static setAccessTokenCookie(obj_id: string, token: string, expiry?: Date) {
        if (expiry == null) {
            expiry = new Date(3000, 1, 1);
        }
        // TODO: use tldjs for this
        const domain = getDomain(WebAPI.apiSettings.url);
        // const domain = new URL(WebAPI.apiSettings.url).hostname;
        Cookies.set(`access_token__${obj_id}`, token,
            {
                expires: expiry,
                // domain: domain,
                domain: '.laxy.io',
                secure: true
            });
    }

    public static async getCsrfToken() {
        const token = WebAPI._getStoredCsrfToken();
        if (!token) {
            try {
                await WebAPI.requestCsrfToken();
                return WebAPI._getStoredCsrfToken();
            } catch (error) {
                throw error;
            }
        } else {
            return token;
        }
    }

    public static _getStoredCsrfToken(): string | undefined {
        return Cookies.get('csrftoken');
    }

    public static async requestCsrfToken(): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(`/api/v1/auth/csrftoken/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async login(user: string, pass: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.post(`/api/v1/auth/login/`,
                {username: user, password: pass}) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async logout(): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(`/api/v1/auth/logout/`) as AxiosResponse;
            // TODO: unset Vuex store user_profile here
        } catch (error) {
            throw error;
        }
    }

    public static async getUserProfile(): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(`/api/v1/user/profile/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async isLoggedIn() {
        try {
            const result = await this.getUserProfile();
            return true;
        } catch (error) {
            return false;
        }
    }

    public static async enaSearch(accession_list: string[]): Promise<AxiosResponse> {
        const accessions = accession_list.join(',');
        const url = `/api/v1/ena/fastqs/?accessions=${accessions}`;
        return await this.fetcher.get(url);
    }

    public static async remoteFilesList(url: string): Promise<AxiosResponse> {
        try {
            const api_url = `/api/v1/remote-browse/?url=${url}`;
            return await this.fetcher.get(api_url);
        } catch (error) {
            throw error;
        }
    }

    public static async getJobs(page: number, page_size: number): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(
                `/api/v1/jobs/?page=${page}&page_size=${page_size}`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getJob(job_id: string, access_token?: string | undefined): Promise<AxiosResponse> {
        try {
            const url = `/api/v1/job/${job_id}/`;
            if (access_token) {
                WebAPI.setQueryParamAccessToken(access_token);
                WebAPI.setAccessTokenCookie(job_id, access_token);
            }
            return await this.fetcher.get(url) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async cancelJob(id: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.patch(
                `/api/v1/job/${id}/`,
                {status: 'cancelled'}) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getJobEventLog(job_id: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(
                `/api/v1/eventlogs/?object_id=${job_id}`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getFileSet(fileset_id: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(
                `/api/v1/fileset/${fileset_id}/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getFileRecord(file_id: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(
                this.viewFileByIdUrl(file_id)) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static viewFileByIdUrl(file_id: string,
                                  filename: string | null = null,
                                  access_token?: string): string {

        let url = `${this.baseUrl}/api/v1/file/${file_id}/`;

        if (filename) {
            url = `${this.baseUrl}/api/v1/file/${file_id}/content/${filename}?access_token=${access_token}`;
        }
        if (access_token) {
            url += `?access_token=${access_token}`;
        }
        return url;
    }

    public static downloadFileByIdUrl(file_id: string,
                                      filename: string | null = null,
                                      access_token?: string): string {
        if (access_token) {
            WebAPI.setQueryParamAccessToken(access_token);
        }
        if (filename) {
            return `${this.baseUrl}/api/v1/file/${file_id}/content/${filename}?download`;
        }
        return `${this.baseUrl}/api/v1/file/${file_id}/?download`;
    }

    public static viewJobFileByPathUrl(job_id: string,
                                       filepath: string,
                                       access_token?: string): string {
        let url = `${this.baseUrl}/api/v1/job/${job_id}/files/${filepath}`;
        if (access_token) {
            url += `?access_token=${access_token}`;
        }
        return url;
    }

    public static downloadJobFileByPathUrl(job_id: string,
                                           filepath: string,
                                           access_token?: string): string {
        if (access_token) {
            WebAPI.setQueryParamAccessToken(access_token);
        }
        return `${this.baseUrl}/api/v1/job/${job_id}/files/${filepath}?download`;
    }

    public static async createSampleset(csvFormData: FormData): Promise<AxiosResponse> {
        try {
            // copy config
            const config = Object.assign({}, WebAPI.axiosConfig);
            // Axios automatically uses Content-Type: multipart/form-data for FormData POSTs,
            // so we don't need to explicitly set the header here
            // config.headers = {'Content-Type': 'multipart/form-data'};
            delete config.data;  // if this is present, form POST fails (empty !)
            // we need to create a new fetcher, if we attempt to reuse the static one with this new config
            // it  won't work (results in empty form POST !)
            const formPostfetcher = axios.create(config);
            return await formPostfetcher.post('/api/v1/sampleset/', csvFormData, config) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    /*
    public static async viewFile(file_id: string,
                                 filename: string | null = null,
                                 contentType = 'text/html') {
        try {
            let url = `/api/v1/file/${file_id}/`;
            if (filename) {
                url = `/api/v1/file/${file_id}/content/${filename}`;
            }
            return await this.fetcher.get(
                url,
                {headers: {'Content-Type': contentType}}) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }
    */

    public static async createAccessToken(job_id: string, expiry_time: string | null): Promise<AxiosResponse> {
        try {
            return await this.fetcher.post(`/api/v1/accesstoken/`,
                {
                    object_id: job_id,
                    content_type: 'job',
                    expiry_time: expiry_time
                }) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getAccessTokens(job_id: string, active: boolean): Promise<AxiosResponse> {
        let url = `/api/v1/accesstokens/?object_id=${job_id}`;
        if (active) {
            url += '&active=1';
        }
        try {
            return await this.fetcher.get(url) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async deleteAccessToken(token_id: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.delete(`/api/v1/accesstoken/${token_id}`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async putJobAccessToken(job_id: string, expiry_time: string | null): Promise<AxiosResponse> {
        try {
            return await this.fetcher.put(`/api/v1/job/${job_id}/accesstoken/`,
                {
                    expiry_time: expiry_time
                }) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getJobAccessToken(job_id: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(`/api/v1/job/${job_id}/accesstoken/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }
}
