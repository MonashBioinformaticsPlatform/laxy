import 'es6-promise';
import axios, { AxiosResponse, AxiosRequestConfig } from 'axios';

import * as Cookies from 'js-cookie';
import { getDomain } from 'tldjs';

import { browserLocale } from './util';
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
        headers: { 'Content-Type': 'application/json' },
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
        // We used tldjs getDomain rather than vanilla new URL(url).hostname
        // since we want to ignore the subdomain (api.laxy.io -> .laxy.io).
        // TODO: NOTE: This has security implications in some hosting contexts
        // (eg, my-laxy-app.example.com -> .example.com; cookie will be
        //  readable by other apps on .example.com )
        const domain = getDomain(WebAPI.apiSettings.url) || '.laxy.io';
        Cookies.set(`access_token__${obj_id}`, token,
            {
                expires: expiry,
                domain: `.${domain}`,
                secure: true,
                sameSite: 'Lax',
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

    public static async ping(): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(`/api/v1/ping/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async login(user: string, pass: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.post(`/api/v1/auth/login/`,
                { username: user, password: pass }) as AxiosResponse;
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

    public static async getAvailablePipelines(): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(
                `/api/v1/pipelines/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async enaSearch(accession_list: string[]): Promise<AxiosResponse> {
        const accessions = accession_list.join(',');
        const url = `/api/v1/ena/fastqs/?accessions=${accessions}`;
        return await this.fetcher.get(url);
    }

    public static async enaSpeciesInfo(accession: string): Promise<AxiosResponse> {
        const url = `/api/v1/ena/species/${accession}`;
        return await this.fetcher.get(url);
    }

    public static async remoteFilesList(url: string, fileglob: string = "*"): Promise<AxiosResponse> {
        try {
            const api_url = `/api/v1/remote-browse/`;
            return await this.fetcher.post(api_url, { url: url, fileglob: fileglob });
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
                { status: 'cancelled' }) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async cloneJob(job_id: string) {
        try {
            return await this.fetcher.post(
                `/api/v1/job/${job_id}/clone/`,
                {}) as AxiosResponse;
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

    public static downloadFileByIdUrl(
        file_id: string,
        filename: string | null = null,
        access_token?: string
    ): string {

        let url: URL = new URL(`${this.baseUrl}/api/v1/file/${file_id}/?download`);
        if (filename) {
            url = new URL(`${this.baseUrl}/api/v1/file/${file_id}/content/${filename}`);
        }
        if (access_token) {
            WebAPI.setQueryParamAccessToken(access_token);
            url.searchParams.append('access_token', access_token);
        }

        return url.toString();
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

    public static downloadJobTarballUrl(job_id: string,
        access_token?: string) {
        let url = `${this.baseUrl}/api/v1/job/${job_id}.tar.gz`;
        if (access_token) {
            url = `${url}?access_token=${access_token}`;
        }
        return url;
    }

    public static async getBlobByUrl(url: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(url, { responseType: 'blob' }) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getFileBlobById(file_id: string, access_token?: string): Promise<AxiosResponse> {
        let url = `${this.baseUrl}/api/v1/file/${file_id}/`;
        if (access_token) {
            url = `${url}?access_token=${access_token}`;
        }
        return WebAPI.getBlobByUrl(url);
    }

    public static async getSampleCart(fileset_id: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(
                `/api/v1/samplecart/${fileset_id}/`) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async createSampleCart(csvFormData: FormData): Promise<AxiosResponse> {
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
            return await formPostfetcher.post('/api/v1/samplecart/', csvFormData, config) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static async getPipelineRun(fileset_id: string): Promise<AxiosResponse> {
        try {
            return await this.fetcher.get(
                `/api/v1/pipelinerun/${fileset_id}/`) as AxiosResponse;
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

    /*
     NOTE: By using the WebAPI.*JobAccessToken methods, we only allow a single sharing link per-job to be created
     (via the UI). The createAccessToken, getAccessTokens methods could be used instead to allow creation of
     multiple tokens per-job.
     */
    public static async updateSharingLink(job_id: string, expires_in: number | string) {
        let expiry_time = null;
        if (typeof expires_in === 'string' && expires_in.includes('Never')) {
            expiry_time = null;
        } else {
            const expiry: Date = new Date();
            expiry.setSeconds(expires_in as number);
            expiry_time = expiry.toISOString();
        }
        try {
            const resp = await WebAPI.putJobAccessToken(job_id, expiry_time);
            return resp;
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

    public static async sendToDegust(file_id: string, access_token?: string): Promise<AxiosResponse> {
        try {
            let url = `/api/v1/action/send-to/degust/${file_id}/`;
            if (access_token) {
                url = `${url}?access_token=${access_token}`;
            }
            // const url = `/api/v1/action/send-to/degust/${file_id}/?force_new=1`;  // for testing
            return await this.fetcher.post(url) as AxiosResponse;
        } catch (error) {
            throw error;
        }
    }

    public static getExternalAppRedirectUrl(appName: string, objectId: string, access_token?: string) {
        let url = `${this.apiSettings.frontendUrl}/#/redirect-external/${appName}/${objectId}`;
        if (access_token) {
            url = `${url}?access_token=${access_token}`;
        }
        return url;
    }
}
