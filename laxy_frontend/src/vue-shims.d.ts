import Vue, { ComponentOptions } from 'vue';
import { Store } from 'vuex';

// This allows TypeScript to import *.vue files (otherwise we get a TS2307 error)
declare module '*.vue' {
  // import Vue from 'vue';
  export default Vue;
}

// from vuex/types/vue.d.ts
// wasn't being discovered in node_modules for some reason
declare module 'vue/types/vue' {
  interface Vue {
    $store: Store<any>;
  }
}

declare module 'vue/types/options' {
  interface ComponentOptions<V extends Vue> {
    store?: Store<any>;
  }
}
