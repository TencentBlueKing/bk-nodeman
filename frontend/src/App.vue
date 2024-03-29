<template>
  <div id="app" :class="[systemCls, { 'notice-show': noticeShow }]">
    <notice-component
      v-if="noticeEnable"
      :api-url="noticeApi"
      @show-alert-change="toggleNotice" />
    <nodeman-navigation>
      <keep-alive :include="cacheViews">
        <router-view />
      </keep-alive>
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
import { IAuthApply, IBkBiz } from '@/types/index';
import BkPaasLogin from '@blueking/paas-login/dist/paas-login.umd';
import NoticeComponent from '@blueking/notice-component-vue2';
import '@blueking/notice-component-vue2/dist/style.css';

@Component({
  name: 'app',
  components: {
    NodemanNavigation,
    PermissionModal,
    BkPaasLogin,
    NoticeComponent,
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
  // 类型: 跑马灯 & dialog; 如果有跑马灯， navigation的高度可能需要减去40px， 避免页面出现滚动条
  private noticeEnable = false;
  private noticeApi = '/notice/announcements/';

  private get loginUrl() {
    return MainStore.loginUrl;
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
  private get noticeShow() {
    return MainStore.noticeShow;
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
    this.noticeEnable = window.PROJECT_CONFIG?.ENABLE_NOTICE_CENTER === 'True';
    this.handleInit();
    MainStore.getPublicKey().then(({ name = '', content = '', cipher_type = 'RSA' }) => {
      this.$safety.updateInstance({
        name,
        publicKey: content,
        type: cipher_type,
      });
    });
  }
  private mounted() {
    window.LoginModal = this.$refs.login;
    bus.$on('show-login-modal', () => {
      const { href, protocol } = window.location;
      if (process.env.NODE_ENV === 'development') {
        window.location.href = LOGIN_DEV_URL + href;
      } else {
        // 目前仅ieod取消登录弹框
        // if (window.PROJECT_CONFIG.RUN_VER === 'ieod') {
        let loginUrl = window.PROJECT_CONFIG.LOGIN_URL;
        if (!/http(s)?:\/\//.test(loginUrl)) {
          loginUrl = `${protocol}//${loginUrl}`;
        }
        if (!loginUrl.includes('?')) {
          loginUrl += '?';
        }
        window.location.href = `${loginUrl}&c_url=${encodeURIComponent(href)}`;
        // } else {
        //   const res = data?.data || {};
        //   if (res.has_plain) {
        //     MainStore.setLoginUrl(res.login_url);
        //     window.LoginModal && window.LoginModal.show();
        //   } else {
        //     window.location.href = res.login_url ? res.login_url : (LOGIN_DEV_URL + href);
        //   }
        // }
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
  public toggleNotice(isShow: boolean) {
    MainStore.updateNoticeShow(isShow);
  }
}
</script>
<!--全局样式-->
<style lang="postcss">
@import "../src/css/reset.css";
@import "../src/css/app.css";
@import "../src/css/install-table.css";
</style>
