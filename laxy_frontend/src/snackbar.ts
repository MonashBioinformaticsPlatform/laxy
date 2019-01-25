import {SET_GLOBAL_SNACKBAR, Store} from './store';

export class Snackbar {

    public static component: any;

    public static flashMessage(message: string, duration: number = 2000) {
        // Snackbar.component.mdDuration = duration;  // shouldn't change props this way
        Store.commit(SET_GLOBAL_SNACKBAR, {message: message, duration: duration});
        Snackbar.component.open();
    }
}
