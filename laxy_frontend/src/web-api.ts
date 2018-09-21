declare function require(path: string): any;

import 'es6-promise';
import axios, {AxiosResponse} from 'axios';

const Cookies = require('js-cookie');

export class WebAPI {

    public static apiSettings = {
        url: process.env.NODE_ENV === 'production' ?
            process.env.LAXY_FRONTEND_API_URL : 'http://localhost:8001',
        frontendUrl: process.env.NODE_ENV === 'production' ?
            process.env.LAXY_FRONTEND_URL : 'http://localhost:8002',
    };

    public static get baseUrl(): string {
        return WebAPI.apiSettings.url;
    }

    /* Axios has this silly quirk where the Content-Type header is removed
       unless you have 'data'. So we add empty data.
     */
    public static readonly axiosConfig = {
        baseURL: WebAPI.baseUrl,
        withCredentials: true,
        xsrfHeaderName: 'X-CSRFToken',
        xsrfCookieName: 'csrftoken',
        headers: {'Content-Type': 'application/json'},
        data: {},
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

    public static getCsrfToken(): string {
        return Cookies.get('csrftoken');
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
            // TODO: unset Vuex store user_profile here
        } catch (error) {
            throw error;
        }
    }

    public static async getUserProfile() {
        try {
            return await this.fetcher.get(`/accounts/profile/`) as AxiosResponse;
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

    public static async getJobEventLog(job_id: string) {
        try {
            return await this.fetcher.get(
                `/api/v1/eventlogs/?object_id=${job_id}`) as AxiosResponse;
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

    public static async getFileRecord(file_id: string) {
        try {
            return await this.fetcher.get(
                this.viewFileByIdUrl(file_id)) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static viewFileByIdUrl(file_id: string,
                                  filename: string | null = null): string {
        if (filename) {
            return `${this.baseUrl}/api/v1/file/${file_id}/content/${filename}`;
        }
        return `${this.baseUrl}/api/v1/file/${file_id}/`;
    }

    public static downloadFileByIdUrl(file_id: string,
                                      filename: string | null = null): string {
        if (filename) {
            return `${this.baseUrl}/api/v1/file/${file_id}/content/${filename}?download`;
        }
        return `${this.baseUrl}/api/v1/file/${file_id}/?download`;
    }

    public static viewJobFileByPathUrl(job_id: string,
                                       filepath: string): string {
        return `${this.baseUrl}/api/v1/job/${job_id}/files/${filepath}`;
    }

    public static downloadJobFileByPathUrl(job_id: string,
                                           filepath: string): string {
        return `${this.baseUrl}/api/v1/job/${job_id}/files/${filepath}?download`;
    }

    public static async createSampleset(csvFormData: FormData) {
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
}
