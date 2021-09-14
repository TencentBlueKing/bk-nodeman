<template>
  <article>
    <!--导航-->
    <bk-navigation
      ref="navigation"
      :hover-enter-delay="300"
      :side-title="nav.headerTitle"
      :navigation-type="nav.navigationType"
      :need-menu="needMenu"
      :default-open="navToggle"
      :class="mainContentClassObj"
      @toggle-click="handleNavToggle">
      <!--icon-->
      <template slot="side-icon">
        <img src="../../images/logoIcon.png" class="nodeman-logo-icon" />
      </template>
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
            <bk-popover ref="helpListRef" class="header-help mr25" trigger="click" theme="light help-list">
              <i class="nodeman-icon nc-help-document-fill"></i>
              <template #content>
                <ul>
                  <li v-for="item in helpList" :key="item.id" @click="handleGotoLink(item)">
                    {{ item.name }}
                  </li>
                </ul>
              </template>
            </bk-popover>
            <bk-popover
              v-if="userList.length"
              theme="light help-list"
              trigger="click"
              placement="bottom-end">
              <div class="header-user">
                {{ currentUser }}
                <i class="bk-icon icon-down-shape"></i>
              </div>
              <template slot="content">
                <ul>
                  <li v-for="(userItem, index) in userList" :key="index" @click="handleUser(userItem)">
                    {{ userItem.name }}
                  </li>
                </ul>
              </template>
            </bk-popover>
            <div class="header-user hover-default" v-else>
              {{ currentUser }}
            </div>
          </div>
        </div>
      </template>
      <!--左侧菜单-->
      <template #menu>
        <NavSideMenu
          :list="sideMenuList"
          v-show="!!sideMenuList.length"
          :current-active="currentActive"
          @select-change="handleSelectChange">
        </NavSideMenu>
      </template>
      <!--内容区域-->
      <template #default>
        <div
          v-bkloading="{ isLoading: nmMainLoading && !mainContentLoading }"
          class="nodeman-main-loading"
          v-show="nmMainLoading && !mainContentLoading">
        </div>
        <div class="nodeman-navigation-content mb20" v-if="!customNavContent">
          <span class="content-icon" v-if="navTitle && needBack" @click="handleBack">
            <i class="nodeman-icon nc-back-left"></i>
          </span>
          <span v-if="navTitle" class="content-header">{{ navTitle }}</span>
        </div>
        <div :style="{ opacity: nmMainLoading ? 0 : 1 }">
          <slot v-if="pagePermission"></slot>
          <exception-page
            v-else
            :class="['exception-page', { 'over-full': pluginViewClass }]"
            type="notPower"
            :sub-title="authSubTitle"
            @click="handleApplyPermission">
          </exception-page>
        </div>
      </template>
    </bk-navigation>
    <log-version :dialog-show.sync="showLog"></log-version>
  </article>
</template>
<script lang="ts">
import { MainStore } from '@/store/index';
import { Component, Ref, Mixins } from 'vue-property-decorator';
import NavSideMenu from '@/components/common/nav-side.vue';
import LogVersion from '@/components/common/log-version.vue';
import ExceptionPage from '@/components/exception/exception-page.vue';
import routerBackMixin from '@/common/router-back-mixin';
import { bus } from '@/common/bus';
import { INavConfig } from '@/types';

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
  },
})
export default class NodemanNavigation extends Mixins(routerBackMixin) {
  @Ref('navigation') private readonly navigation!: any;
  @Ref('helpListRef') private readonly helpListRef!: any;

  // 导航配置
  private nav ={
    navigationType: 'top-bottom',
    headerTitle: window.i18n.t('蓝鲸节点管理'),
  };
  private currentUser = window.PROJECT_CONFIG.USERNAME;
  private navToggle = false;
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
  ];
  private userList: IUserItem[] = [];
  private showLog = false;
  private subTitleMap: { [key: string]: string } = {
    agentStatus: window.i18n.t('查看agentAuth'),
    agentEdit: window.i18n.t('操作agentAuth'),
    agentSetup: window.i18n.t('操作agentAuth'),
    agentImport: window.i18n.t('操作agentAuth'),
    setupCloudManager: window.i18n.t('安装proxyAuth'),
    pluginOld: window.i18n.t('查看插件Auth'),
    taskList: window.i18n.t('查看任务历史Auth'),
    addCloudManager: window.i18n.t('创建云区域权限'),
    editCloudManager: window.i18n.t('编辑云区域权限'),
    cloudManagerDetail: window.i18n.t('查看云区域权限'),
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
  private get mainContentLoading() {
    return MainStore.mainContentLoading;
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
  // 左侧导航list
  private get sideMenuList() {
    if (this.activeIndex === -1) return [];
    return this.navList[this.activeIndex].children || [];
  }
  // 子菜单默认激活项
  private get currentActive() {
    if (this.activeIndex === -1) return 0;
    return this.navList[this.activeIndex].currentActive || 0;
  }
  // 导航title
  private get navTitle() {
    return MainStore.currentNavTitle || this.$route.meta.title;
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
  private mounted() {
    this.resetNavToggle();
    if (window.PROJECT_CONFIG.RUN_VER !== 'ieod') {
      this.userList.push({ id: 'LOGOUT', name: window.i18n.t('退出') });
    }
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
  private handleUser(userItem: IUserItem) {
    if (userItem.id === 'LOGOUT') {
      if (NODE_ENV === 'development') {
        window.location.href = LOGIN_DEV_URL + window.location.href;
      } else {
        window.location.href = `${window.PROJECT_CONFIG.BK_PAAS_HOST}/console/accounts/logout/`;
      }
    }
  }
  private handleApplyPermission() {
    bus.$emit('show-permission-modal', { params: { apply_info: [{ action: MainStore.bizAction }] } });
  }
  private handleNavToggle(value: boolean) {
    window.localStorage.setItem('navToggle', `${value}`);
  }
  private resetNavToggle() {
    const value = window.localStorage.getItem('navToggle');
    if (this.navToggle === (value === 'false')) {
      this.navigation.handleClick && this.navigation.handleClick();
    }
  }
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";
  @import "@/css/variable.css";

  $navColor: #96a2b9;
  $navHoverColor: #d3d9e4;
  $headerColor: #313238;

  >>> .navigation-container {
    /* stylelint-disable-next-line declaration-no-important */
    max-width: unset !important;
    z-index: 0;
  }
  >>> .bk-navigation-header {
    z-index: 1000;
  }
  >>> .bk-navigation-wrapper .navigation-nav .nav-slider-list {
    overflow-x: hidden;
  }
  .nodeman-main-loading {
    /* stylelint-disable-next-line declaration-no-important */
    position: absolute !important;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }
  .default-content {
    >>> .bk-navigation-wrapper .container-content {
      padding: 20px 60px 0 60px;
    }
  }
  .custom-content {
    >>> .bk-navigation-wrapper .container-content {
      padding: 0;
    }
  }
  .container-background {
    >>> .bk-navigation-wrapper .container-content {
      background: $whiteColor ;
    }
  }
  .nodeman-logo-icon {
    width: 28px;
    height: 28px;
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
        .header-help,
        .header-user {
          &:hover {
            color: $navHoverColor;
          }
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
</style>
