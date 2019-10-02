import Vuex from 'vuex';

declare module 'vuex' {
    interface Store<S> {
        get(path: string): any;

        set(path: string, value: any): any;

        copy(path: string): any;
    }
}
