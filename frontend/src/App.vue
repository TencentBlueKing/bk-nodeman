<template>
  <div id="app" :class="systemCls">
    <nodeman-navigation>
      <div v-bkloading="{ isLoading: mainContentLoading, opacity: 1 }">
        <keep-alive :include="cacheViews">
          <router-view v-show="!mainContentLoading" />
        </keep-alive>
      </div>
    </nodeman-navigation>
    <permission-modal ref="permissionModal"></permission-modal>
    <bk-paas-login ref="login" :login-url="loginUrl"></bk-paas-login>
  </div>
</template>
<script lang="ts">
import { MainStore } from '@/store/index';
import { bus } from '@/common/bus';
import NodemanNavigation from '@/components/common/navigation.vue';
import PermissionModal from '@/components/auth/PermissionModal.vue';
import { STORAGE_KEY_BIZ, STORAGE_KEY_FONT } from '@/config/storage-key';
import { Vue, Component, Ref, Watch } from 'vue-property-decorator';
import { IAuthApply, IBkBiz, ILoginRes } from '@/types/index';
import BkPaasLogin from '@blueking/paas-login/dist/paas-login.umd';

@Component({
  name: 'app',
  components: {
    NodemanNavigation,
    PermissionModal,
    BkPaasLogin,
  },
})
export default class App extends Vue {
  @Ref('permissionModal') private readonly permissionModal!: any;

  private routerKey = +new Date();
  private systemCls = 'mac';
  private fontList = [
    {
      id: 'standard',
      name: window.i18n.t('标准'),
      checked: true,
    },
    {
      id: 'large',
      name: window.i18n.t('偏大'),
      checked: false,
    },
  ];

  private get loginUrl() {
    return MainStore.loginUrl;
  }
  private get mainContentLoading() {
    return MainStore.mainContentLoading;
  }
  private get bkBizList() {
    return MainStore.bkBizList;
  }
  private get selectedBiz() {
    return MainStore.selectedBiz;
  }
  private get cacheViews() {
    return MainStore.cacheViews;
  }

  @Watch('bkBizList')
  private handleBizListChange(v: IBkBiz[]) {
    const selectedBiz = this.selectedBiz.filter(id => v.find(data => data.bk_biz_id === id));
    MainStore.setSelectedBiz(selectedBiz);
  }

  private created() {
    const platform = window.navigator.platform.toLowerCase();
    if (platform.indexOf('win') === 0) {
      this.systemCls = 'win';
    }
    MainStore.setLanguage(window.language);
    this.handleInit();
  }
  private mounted() {
    window.LoginModal = this.$refs.login;
    bus.$on('show-login-modal', (data: ILoginRes) => {
      if (process.env.NODE_ENV === 'development') {
        window.location.href = LOGIN_DEV_URL + window.location.href;
      } else {
        const res = data?.data || {};
        if (res.has_plain) {
          MainStore.setLoginUrl(res.login_url);
          window.LoginModal && window.LoginModal.show();
        } else {
          const href = res.login_url ? res.login_url : (LOGIN_DEV_URL + window.location.href);
          window.location.href = href;
        }
      }
    });
    bus.$on('show-permission-modal', (data: { trigger: 'request' | 'click', params: IAuthApply }) => {
      this.permissionModal.show(data);
    });
    this.$nextTick(() => {
      window.addEventListener('resize', () => {
        MainStore.updateScreenInfo(window.innerHeight);
      });
    });
  }
  /**
   * 初始化应用
   */
  private handleInit() {
    let selectedBiz = [];
    if (window.localStorage) {
      try {
        selectedBiz = JSON.parse(window.localStorage.getItem(STORAGE_KEY_BIZ) as string) || [];
        const font = window.localStorage.getItem(STORAGE_KEY_FONT);
        if (font && this.fontList.find(item => item.id === font)) {
          this.fontList.forEach((item) => {
            item.checked = font === item.id;
          });
        }
      } catch (_) {
        selectedBiz = [];
      }
    }
    MainStore.updatePermissionSwitch(window.PROJECT_CONFIG.USE_IAM === 'True');
    MainStore.setFont(this.fontList);
    MainStore.setSelectedBiz(selectedBiz);
  }
}
</script>
<!--全局样式-->
<style>
@import "../src/css/reset.css";
@import "../src/css/app.css";
@import "../src/css/install-table.css";
</style>
