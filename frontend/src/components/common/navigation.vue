<template>
  <article class="nodeman-wrapper">
    <!--导航-->
    <bk-navigation
      ref="navigation"
      :hover-enter-delay="300"
      :navigation-type="nav.navigationType"
      :need-menu="needMenu"
      :default-open="navToggle"
      :class="mainContentClassObj"
      @hover="navHover = true"
      @leave="() => !bizSelectFocus && (navHover = false)"
      @toggle-click="handleNavToggle">
      <!--icon-->
      <div slot="side-header" class="nav-header" @click="$router.push('/')">
        <img src="../../images/logoIcon.png" class="nodeman-logo-icon" />
        <span class="title-desc">{{ nav.headerTitle }}</span>
      </div>
      <!--顶部导航-->
      <template #header>
        <div class="nodeman-navigation-header">
          <div class="nav-left">
            <ol class="header-nav" v-test.nav="'head'">
              <li v-for="(route, index) in navList"
                  :key="index"
                  class="header-nav-item"
                  :class="{ 'item-active': route.name === currentNavName }"
                  @click="handleChangeMenu(route, index)">
                {{ $t(route.title) }}
              </li>
            </ol>
          </div>
          <div class="nav-right">
            <MixinsControlDropdown ext-cls="menu-dropdown">
              <div class="header-nav-btn header-nav-icon-btn">
                <i :class="`nodeman-icon nc-lang-${language}`" />
              </div>
              <template #content>
                <ul class="bk-dropdown-list">
                  <li class="dropdown-list-item" v-for="item in langList" :key="item.id" @click="toggleLang(item)">
                    <i :class="`nodeman-icon nc-lang-${item.id}`" /> {{ item.name }}
                  </li>
                </ul>
              </template>
            </MixinsControlDropdown>
            <MixinsControlDropdown ext-cls="menu-dropdown">
              <div class="header-nav-btn header-nav-icon-btn">
                <i class="nodeman-icon nc-help-document-fill"></i>
              </div>
              <template #content>
                <ul class="bk-dropdown-list">
                  <li class="dropdown-list-item" v-for="item in helpList" :key="item.id" @click="handleGotoLink(item)">
                    {{ item.name }}
                  </li>
                </ul>
              </template>
            </MixinsControlDropdown>
            <MixinsControlDropdown ext-cls="menu-dropdown">
              <div class="header-user header-nav-btn">
                {{ currentUser }}
                <i class="bk-icon icon-down-shape"></i>
              </div>
              <template #content>
                <ul class="bk-dropdown-list">
                  <li
                    class="dropdown-list-item"
                    v-for="(userItem, index) in userList"
                    :key="index"
                    @click="handleUser(userItem)">
                    {{ userItem.name }}
                  </li>
                </ul>
              </template>
            </MixinsControlDropdown>
          </div>
        </div>
      </template>
      <!--左侧菜单-->
      <template #menu>
        <div class="nm-menu-biz" v-if="showBizSelect">
          <div class="menu-biz-shrink-text">{{ navBizShrinkText }}</div>
          <bk-biz-select
            v-model="biz"
            ext-cls="menu-biz-select"
            :min-width="36"
            :popover-min-width="235"
            :auto-request="autoRequest"
            :placeholder="$t('全部业务')"
            @change="handleBizChange"
            @toggle="handleBizToggle">
          </bk-biz-select>
        </div>
        <NavSideMenu
          :list="sideMenuList"
          v-show="!!sideMenuList.length"
          :current-active="currentActive"
          @select-change="handleSelectChange">
        </NavSideMenu>
      </template>
      <!--内容区域-->
      <template #default>
        <div v-bkloading="{ isLoading: nmMainLoading }" class="nodeman-main-loading" v-show="nmMainLoading" />
        <div class="page-wrapper">
          <div class="page-header mb20" v-if="!customNavContent">
            <span class="content-icon" v-if="navTitle && needBack" @click="handleBack">
              <i class="nodeman-icon nc-back-left"></i>
            </span>
            <span v-if="navTitle" class="content-header">{{ navTitle }}</span>
          </div>
          <slot v-if="pagePermission"></slot>
          <exception-page
            v-else
            :class="['exception-page', { 'over-full': pluginViewClass }]"
            :style="{ opacity: nmMainLoading ? 0 : 1 }"
            type="notPower"
            :sub-title="authSubTitle"
            @click="handleApplyPermission">
          </exception-page>
        </div>
      </template>
    </bk-navigation>
    <log-version v-model="showLog"></log-version>
  </article>
</template>
<script lang="ts">
import { MainStore } from '@/store/index';
import { Component, Ref, Mixins, Watch } from 'vue-property-decorator';
import NavSideMenu from '@/components/common/nav-side.vue';
import LogVersion from '@/components/common/log-version.vue';
import MixinsControlDropdown from '@/components/common/MixinsControlDropdown.vue';
import ExceptionPage from '@/components/exception/exception-page.vue';
import routerBackMixin from '@/common/router-back-mixin';
import { bus } from '@/common/bus';
import { INavConfig, ISideMenuConfig } from '@/types';

interface IUserItem {
  id: string
  name: string
  href?: string
}

@Component({
  name: 'nodeman-navigation',
  components: {
    NavSideMenu, // 左侧导航组件
    LogVersion,
    ExceptionPage,
    MixinsControlDropdown,
  },
})
export default class NodemanNavigation extends Mixins(routerBackMixin) {
  @Ref('navigation') private readonly navigation!: any;
  @Ref('helpListRef') private readonly helpListRef!: any;

  // 导航配置
  public biz: number[] = [];
  private nav ={
    navigationType: 'top-bottom',
    headerTitle: window.i18n.t('蓝鲸节点管理'),
  };
  private currentUser = window.PROJECT_CONFIG.USERNAME;
  private navToggle = false;
  private navHover = false;
  private bizSelectFocus = false;
  private helpList = [
    {
      id: 'DOC',
      name: this.$t('产品文档'),
      href: window.PROJECT_CONFIG.BK_DOCS_CENTER_URL,
    },
    {
      id: 'VERSION',
      name: this.$t('版本日志'),
    },
    {
      id: 'FAQ',
      name: this.$t('问题反馈'),
      href: 'https://bk.tencent.com/s-mart/community',
    },
    {
      id: 'FAQ',
      name: this.$t('开源社区'),
      href: window.PROJECT_CONFIG.BKAPP_NAV_OPEN_SOURCE_URL,
    },
  ];
  private langList = [
    {
      id: 'zh-cn', // zhCN
      name: '中文',
    },
    {
      id: 'en', // enUS
      name: 'English',
    },
  ];
  private userList: IUserItem[] = [
    { id: 'LOGOUT', name: window.i18n.t('退出登录') },
  ];
  private showLog = false;
  private subTitleMap: { [key: string]: string } = {
    agentStatus: window.i18n.t('查看agentAuth'),
    agentEdit: window.i18n.t('操作agentAuth'),
    agentSetup: window.i18n.t('操作agentAuth'),
    agentImport: window.i18n.t('操作agentAuth'),
    setupCloudManager: window.i18n.t('安装proxyAuth'),
    pluginOld: window.i18n.t('查看插件Auth'),
    taskList: window.i18n.t('查看任务历史Auth'),
    addCloudManager: window.i18n.t('创建管控区域权限'),
    editCloudManager: window.i18n.t('编辑管控区域权限'),
    cloudManagerDetail: window.i18n.t('查看管控区域权限'),
  };

  private get navList() {
    return MainStore.navList.filter(item => !item.disabled);
  }
  private get currentNavName() {
    return MainStore.currentNavName;
  }
  private get nmMainLoading() {
    return MainStore.nmMainLoading;
  }
  private get customNavContent() {
    return MainStore.customNavContent;
  }
  // 当前菜单激活项
  private get activeIndex() {
    return this.navList.findIndex(item => item.name === this.currentNavName);
  }
  // 是否需要左侧导航
  private get needMenu() {
    if (this.activeIndex === -1) return false;
    return !!this.navList[this.activeIndex as number].children?.length;
  }
  // 根据开关隐藏Agent包管理菜单
  private get navListHideAgentPkg() {
    // 深拷贝侧边栏菜单列表
    const navList = JSON.parse(JSON.stringify(this.navList[this.activeIndex].children || [])) as ISideMenuConfig[];
    // 过滤隐藏Agent包管理菜单
    navList?.forEach((item) => {
      if (item.name === 'nav_Agent状态') {
        item.children = item.children?.filter((child: { name: string; }) => child.name !== 'agentPackage');
      }
    });
    return navList;
  }
  private async created() {
    // 获取开关状态
    await this.getAgentPackageUI();
  }
  // 左侧导航list
  private get sideMenuList() {
    if (this.activeIndex === -1) return [];
    // 根据开关状态过滤agent包管理菜单
    const agentSwitch = MainStore.ENABLE_AGENT_PACKAGE_UI;
    const menuList = !agentSwitch ? this.navListHideAgentPkg : this.navList[this.activeIndex].children;
    return menuList || [];
  }
  // 子菜单默认激活项
  private get currentActive() {
    // if (this.activeIndex === -1) return 0;
    return this.$route.meta.parentName || this.$route.name;
  }
  // 导航title
  private get navTitle() {
    return this.$t(MainStore.currentNavTitle || this.$route.meta.title);
  }
  // 是否需要返回
  private get needBack() {
    return this.$route.meta.needBack;
  }
  // 内容区域统一样式
  private get mainContentClassObj() {
    return {
      'default-content': !this.needMenu && !this.customNavContent,
      'container-background': this.needBack && !MainStore.isDefaultContent,
      'custom-content': this.customNavContent,
      'nav-shrink': !this.navToggle && !this.navHover,
      'select-focus': this.bizSelectFocus,
    };
  }
  private get pagePermission() {
    return MainStore.permissionSwitch ? MainStore.hasPagePermission : true;
  }
  // 旧版插件无副标题，先特殊处理
  private get pluginViewClass() {
    return MainStore.permissionSwitch && ['cloudManagerDetail', 'pluginOld'].includes(this.$route.name as string);
  }
  private get authSubTitle() {
    const { name, params } = this.$route;
    let routeName = name as string;
    if (name === 'addCloudManager' && params.type === 'edit') {
      routeName = 'editCloudManager';
    }
    return this.subTitleMap[routeName];
  }
  private get showBizSelect() {
    return  this.activeIndex === 0;
  }
  private get navBizShrinkText() {
    if (!this.selectedBiz.length) {
      return window.i18n.t('全');
    }
    return this.selectedBiz.length > 1 ? this.selectedBiz.length : MainStore.selectedBizName[0]?.[0];
  }
  private get autoRequest() {
    return !MainStore.permissionSwitch;
  }
  private get selectedBiz() {
    return MainStore.selectedBiz;
  }
  private get language() {
    return MainStore.language;
  }

  @Watch('selectedBiz')
  public watchBizChange(value: number[]) {
    this.biz = [...value];
  }

  private mounted() {
    this.resetNavToggle();
    this.biz = [...this.selectedBiz];
  }
  /**
   * 切换菜单
   * @param {Object} route
   */
  private handleChangeMenu(route: INavConfig) {
    if (this.$route.name === route.name) return;
    const name = route.children && !!route.children.length ? route.defaultActive : route.name;
    this.$router.push({
      name,
    });
  }
  /**
   * 子菜单切换
   * @param {String} name
   */
  private handleSelectChange(name: string) {
    MainStore.updateSubMenuName({ name });
  }
  /**
   * 返回
   */
  private handleBack() {
    this.routerBack();
  }
  private toggleLang(item: IUserItem) {
    if (item.id !== this.language) {
      const {
        BK_COMPONENT_API_URL: overwriteUrl = '',
        BK_DOMAIN: domain = '',
      } = window.PROJECT_CONFIG;

      const api = `${overwriteUrl}/api/c/compapi/v2/usermanage/fe_update_user_language/?language=${item.id}`;
      const scriptId = 'jsonp-script';
      const prevJsonpScript = document.getElementById(scriptId);
      if (prevJsonpScript) {
        document.body.removeChild(prevJsonpScript);
      }
      const scriptEl = document.createElement('script');
      scriptEl.type = 'text/javascript';
      scriptEl.src = api;
      scriptEl.id = scriptId;
      document.body.appendChild(scriptEl);

      const today = new Date();
      today.setTime(today.getTime() + 1000 * 60 * 60 * 24);
      document.cookie = `blueking_language=${item.id};path=/;domain=${domain};expires=${today.toUTCString()}`;
      location.reload();
    }
  }
  /**
   * 系统外链
   */
  private handleGotoLink(item: IUserItem) {
    switch (item.id) {
      case 'DOC':
      case 'FAQ':
        item.href && window.open(item.href);
        break;
      case 'VERSION':
        this.showLog = true;
        break;
    }
    this.helpListRef && this.helpListRef.instance.hide();
  }
  private async handleUser(userItem: IUserItem) {
    if (userItem.id === 'LOGOUT') {
      if (NODE_ENV === 'development') {
        window.location.href = LOGIN_DEV_URL + window.location.href;
      } else {
        this.$http.get?.(`${window.PROJECT_CONFIG.SITE_URL}logout/`);
        // window.location.href = `${window.PROJECT_CONFIG.BK_PAAS_HOST}/console/accounts/logout/`;
        // window.location.href = `${window.PROJECT_CONFIG.LOGIN_URL}?&c_url=${window.location}`;
      }
    }
  }
  private handleApplyPermission() {
    bus.$emit('show-permission-modal', { params: { apply_info: [{ action: MainStore.bizAction }] } });
  }
  private handleNavToggle(value: boolean) {
    this.navToggle = value;
    this.navHover = value;
    window.localStorage.setItem('navToggle', `${value}`);
  }
  private handleBizToggle(toggle: boolean) {
    this.bizSelectFocus = toggle;
    this.navHover = this.navToggle ? false : toggle;
  }
  private resetNavToggle() {
    const value = window.localStorage.getItem('navToggle');
    if (this.navToggle === (value === 'false')) {
      this.navigation.handleClick && this.navigation.handleClick();
    }
  }
  public handleBizChange(newBizIds: number[]) {
    MainStore.setSelectedBiz(newBizIds);
  }
  public async getAgentPackageUI() {
    await MainStore.getAgentPackageUI();
  }
}
</script>
<style lang="postcss">
@import "@/css/mixins/nodeman.css";
@import "@/css/variable.css";

$navColor: #96a2b9;
$navHoverColor: #d3d9e4;
$headerColor: #313238;

.nodeman-wrapper {

  .menu-biz-shrink-text {
    opacity: 0;
    position: absolute;
    top: 0;
    left: 12px;
    right: 12px;
    height: 32px;
    line-height: 32px;
    text-align: center;
    color: #63656e;
    background: #f0f1f5;
    z-index: 101;
    pointer-events: none;
    transition: all .5s ease-in;
  }

  .nav-shrink {
    >>> .bk-select-angle,
    >>> .bk-select-clear {
      display: none;
    }
    /* >>> .bk-navigation-menu-group:first-child .group-name{
      margin: 0 14px;
      transition: all .5s ease-in;
    } */
    .menu-biz-select .bk-select-name {
      color: transparent;
    }
    .menu-biz-shrink-text {
      opacity: 1;
    }
    .menu-biz-select {
      opacity: 0;
    }
  }
  .select-focus {
    >>> .nav-slider {
      width: 260px!important;
    }
  }
  .nm-menu-biz {
    position: relative;
    margin-bottom: 4px;
    padding: 0 12px;
    height: 32px;

    .menu-biz-select {
      opacity: 1;
      border: 1px solid #f0f1f5;
      background-color: #f0f1f5;
      /* opacity: 1; */
      /* transition: all .1s linear 88s; */
      transition: all .5s ease-in;
      &.is-focus {
        border-color: #3a84ff;
      }
      &::before {
        width: calc(100% - 20px);
        overflow: hidden;
      }
      >>> .bk-tooltip-ref {
        overflow: hidden;
      }
    }
  }
  .nav-content-wrapper {
    height: 100%;
    & > div {
      height: 100%;
    }
  }
  .nodeman-main-loading {
    /* stylelint-disable-next-line declaration-no-important */
    position: absolute !important;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }
  .nodeman-logo-icon {
    width: 28px;
    height: 28px;
  }
  .nav-header {
    display: flex;
    align-items: center;
    height: 100%;
    cursor: pointer;
    .title-desc {
      margin-left: 10px;
      font-weight: 400;
      color: #eaebf0;
    }
  }
  .nodeman-navigation {
    &-header {
      width: 100%;
      overflow: hidden;
      font-size: 14px;

      @mixin layout-flex row, center, space-between;
      .nav-right {
        color: $navColor;
        cursor: pointer;

        @mixin layout-flex row, center;
        .header-nav-btn {
          @mixin layout-flex row, center, center;
          min-width: 32px;
          min-height: 32px;
          margin-left: 12px;
          padding: 0 7px;
        }
        .header-nav-icon-btn {
          width: 32px;
          font-size: 18px;
        }
        /deep/ .dropdown-active .header-nav-icon-btn {
          background: rgba(255, 255, 255, .1);
          border-radius: 16px;
          color: #fff;
        }
        .hover-default:hover {
          color: $navColor;
          cursor: default;
        }
      }
      .header-user {
        @mixin layout-flex row, center;
        i {
          margin-left: 8px;
        }
      }
      .header-nav {
        padding: 0;
        margin: 0;

        @mixin layout-flex;
        &-item {
          margin-right: 40px;
          list-style: none;
          height: 50px;
          color: $navColor;

          @mixin layout-flex row, center;
          &.item-active {
            color: $whiteColor;
          }
          &:hover {
            cursor: pointer;
            color: $navHoverColor;
          }
        }
      }
    }
    &-content {
      line-height: 20px;

      @mixin layout-flex row, center;
      .content-icon {
        position: relative;
        height: 20px;
        top: -4px;
        margin-left: -7px;
        font-size: 28px;
        color: $primaryFontColor;
        cursor: pointer;
      }
      .content-header {
        font-size: 16px;
        color: $headerColor;
      }
    }
  }
  .exception-page {
    height: calc(100% - 60px);
    &.over-full {
      height: 100%;
    }
  }

  @keyframes delayShow {
    form {
      display: block;
    }
    to {
      display: none;
    }
  }
}
</style>
