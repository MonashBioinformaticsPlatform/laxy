/*
# vuex-class-state2way

From: https://github.com/scleriot/vuex-class-state2way
License: MIT

TypeScript decorator to create getters/setters for a Vuex state.

The main purpose is to use `v-model` directive without the overhead
of manually creating simple getters and setters.

Check [vuex-class](https://github.com/ktsn/vuex-class) repository for
a lot more Vuex decorators!

## Dependencies

- [Vue](https://github.com/vuejs/vue)
- [Vuex](https://github.com/vuejs/vuex)
- [vue-class-component](https://github.com/vuejs/vue-class-component)

## Installation

```bash
$ npm install --save vuex-class-state2way
# or
$ yarn add vuex-class-state2way
```

## Usage

* Get `variable_name` from the state, and commit `"mutation name"`
  to update this variable in the state

```ts
@State2Way("mutation name") variable_name
```

* Get `variable_name` from the state and set its value to the variable
  `other_name`, and commit `"mutation name"` to update this variable in the state

```ts
@State2Way("mutation name", "variable_name") other_name
```

* To get a deep value, you can do both:
```ts
@State2Way("mutation name", state => state.foo.bar) fooBar // you get type checking
@State2Way("mutation name", "foo.bar") fooBar
```

## Example

```ts
import Vue from 'vue'
import Component from 'vue-class-component'
import { State2Way } from 'vuex-class-state2way'

@Component
export class Comp extends Vue {
    @State2Way('updateFoo', 'foo') stateFoo
    @State2Way('updateBar') bar
    @State2Way('updateFooBar', 'foobar.example') stateFooBarExample
    @State2Way('updateFooBar', state => state.foobar.example) stateFooBarExemple2
}
```
*/

import {createDecorator} from 'vue-class-component';

function getDeepValue(st: string, obj: any) {
    return st.replace(/\[([^\]]+)]/g, '.$1')
        .split('.')
        .reduce(function(o, p) {
            return o[p];
        }, obj);
}

type functionGetState = (state: any) => any;

export function State2Way(mutation: string, stateVariable?: string | functionGetState): any {
    return createDecorator((componentOptions, k) => {
        if (!componentOptions.computed) {
            componentOptions.computed = {};
        }

        componentOptions.computed[k] = {
            get() {
                if (typeof stateVariable === 'string') {
                    return stateVariable ? getDeepValue(stateVariable,
                        (this as any).$store.state) : (this as any).$store.state[k];
                } else if (stateVariable) {
                    return stateVariable((this as any).$store.state);
                }
            },
            set(val) {
                (this as any).$store.commit(mutation, val);
            }
        };
    });
}
