<template>
  <div class="bk-login-dialog" v-if="isShow">
    <div class="bk-login-wrapper">
      <iframe :src="iframeSrc" scrolling="no" border="0" :width="iframeWidth" :height="iframeHeight"></iframe>
    </div>
  </div>
</template>

<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';
import { ILoginData } from '@/types/index';

@Component({ name: 'app-auth' })
export default class AppAuth extends Vue {
  private iframeSrc= '';
  private iframeWidth= 500;
  private iframeHeight= 500;
  private isShow= false;
  public hideLoginModal() {
    this.isShow = false;
  }
  public showLoginModal(data: ILoginData) {
    const url = data.login_url;
    if (!url) {
      console.warn('The response don\'t return login_url');
      return;
    }
    this.iframeSrc = url;
    const iframeWidth = data.width;
    if (iframeWidth) {
      this.iframeWidth = iframeWidth;
    }
    const iframeHeight = data.height;
    if (iframeHeight) {
      this.iframeHeight = iframeHeight;
    }
    setTimeout(() => {
      this.isShow = true;
    }, 1000);
  }
}
</script>

<style scoped>
    @import "./index.css";
</style>
