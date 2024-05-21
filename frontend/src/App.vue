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
import { showLoginModal } from '@blueking/login-modal';

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
    bus.$on('show-login-modal', (message: any) => {
      // static_url： '/static/' or '/'
      const static_url = window.PROJECT_CONFIG?.STATIC_URL ? window.PROJECT_CONFIG.STATIC_URL : '/';
      // 登录成功之后的回调地址，用于执行关闭登录窗口或刷新父窗口页面等动作
      const successUrl = `${window.location.origin}${static_url}login_success.html`;
      const { href, protocol } = window.location;
      let loginUrl = '';
      if (process.env.NODE_ENV === 'development') {
        // 本地登录地址不需要bknodeman前缀，成功回调地址由searchParams设置
        loginUrl = LOGIN_DEV_URL.replace('bknodeman.','')
      } else {
        loginUrl = window.PROJECT_CONFIG.LOGIN_URL;
        if (!/http(s)?:\/\//.test(loginUrl)) {
          loginUrl = `${protocol}//${loginUrl}`;
        }
      }
      // 处理登录地址为登录小窗需要的格式，主要是设置c_url参数
      const loginURL = new URL(loginUrl);
      // 注销登录添加is_from_logout参数，用于在注销登录时，清除bk_token
      message === 'logout' && loginURL.searchParams.set('is_from_logout', '1');
      loginURL.searchParams.set('c_url', successUrl);
      const pathname = loginURL.pathname.endsWith('/') ? loginURL.pathname : `${loginURL.pathname}/`;
      loginUrl = `${loginURL.origin}${pathname}plain/${loginURL.search}`;
      // 使用登录弹框登录
      showLoginModal({ loginUrl });
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
