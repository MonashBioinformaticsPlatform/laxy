<template>
  <md-layout md-column md-gutter>
    <md-layout style="margin: 24px" md-vertical-align="stretch" :md-column-medium="true" :md-row-large="true">
      <md-whiteframe md-elevation="2" class="pad-32">

        <md-card>
          <md-card-header>
            <md-card-header-text class="pad-16">
              <div class="md-title">User Profile</div>
              <div class="md-subhead">{{ full_name }}</div>
            </md-card-header-text>

            <md-card-media class="pad-16">
              <img :src="profile_pic_url" alt="People">
            </md-card-media>
          </md-card-header>

          <md-card-content>
            <md-table>
              <md-table-row>
                <md-table-cell><strong>Name</strong></md-table-cell>
                <md-table-cell>{{ full_name }}</md-table-cell>
              </md-table-row>
              <md-table-row>
                <md-table-cell><strong>Username</strong></md-table-cell>
                <md-table-cell>{{ username }}</md-table-cell>
              </md-table-row>
              <md-table-row>
                <md-table-cell><strong>Email address</strong></md-table-cell>
                <md-table-cell>{{ email }}</md-table-cell>
              </md-table-row>
              <md-table-row>
                <md-table-cell><strong>Laxy user ID</strong></md-table-cell>
                <md-table-cell>{{ user_id }}</md-table-cell>
              </md-table-row>
            </md-table>
          </md-card-content>
        </md-card>

        <p class="pad-16">
          To authenticate scripts, curl, or AI agents, create a named
          <router-link :to="{ name: 'api-keys' }">API key</router-link>.
        </p>
      </md-whiteframe>
    </md-layout>
  </md-layout>
</template>

<script lang="ts">
import get from "lodash-es/get";
import isString from "lodash-es/isString";

import Vue from "vue";
import Component from "vue-class-component";

@Component({})
export default class UserProfile extends Vue {

  public get full_name(): string {
    const name = get(this.$store.state.user_profile, "full_name", null);
    if (!name || (isString(name) && !name.trim())) {
      return "Anonymous User";
    }
    return name;
  }

  public get username(): string {
    return get(this.$store.state.user_profile, "username", "anonymous");
  }

  public get user_id(): string {
    return get(this.$store.state.user_profile, "id", null);
  }

  public get email(): string {
    return get(this.$store.state.user_profile, "email", null);
  }

  public get profile_pic_url(): string {
    return get(this.$store.state.user_profile, "profile_pic", null);
  }
}
</script>

<style lang="scss" scoped>
.md-card {
  width: 100%;
}

.md-whiteframe {
  width: 100%;
}
</style>
