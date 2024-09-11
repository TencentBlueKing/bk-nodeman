import { VuexModule, Module, Action, Mutation } from 'vuex-module-decorators';
import Vue from 'vue';
import http from '@/api';
import navList from '@/router/navigation-config';
import { retrieveBiz, fetchTopo } from '@/api/modules/cmdb';
import { retrieveGlobalSettings, getFilterCondition, getAgentPackageUI } from '@/api/modules/meta';
import { fetchPublicKeys } from '@/api/modules/rsa';
import {
  fetchPermission,
  listCloudPermission,
  listPluginInstancePermission,
  listStartegyPermission,
  listPackagePermission,
} from '@/api/modules/permission';
import axios from 'axios';
import { INavConfig, ISubNavConfig, IBkBiz, ICheckItem, IIsp, IAuthApply, IKeyItem } from '@/types';
import { Route } from 'vue-router';

const permissionMethodsMap: Dictionary = {
  cloud: listCloudPermission,
  plugin: listPluginInstancePermission,
  startegy: listStartegyPermission,
  package: listPackagePermission,
};

// eslint-disable-next-line new-cap
@Module({ name: 'main', namespaced: true })
export default class Main extends VuexModule {
  public nmMainLoading = true; // 全局可视区域加载
  // 系统当前登录用户
  public user = {};
  // 导航信息
  public navList: INavConfig [] = navList;
  // 当前一级导航name
  public currentNavName = '';
  // 三级导航标题
  public currentNavTitle = '';
  // 是否自定义导航内容
  public customNavContent = false;
  // 是否展示默认背景
  public isDefaultContent = false;
  // 业务范围
  public bkBizList: IBkBiz[] = [];
  // 当前选择的业务
  public selectedBiz: number[] = [];
  public selectedBizName: string[] = [];
  // 云服务商列表
  public ispList: IIsp[] = [];
  // 表格字号设置
  public fontSize = '';
  public fontList: ICheckItem[] = [];
  // 语音类型
  public language = '';
  // 权限中心开关
  public permissionSwitch = false;
  // 业务权限细化
  public bizAction = '';
  // 当前页面是否有
  public hasPagePermission = true;
  // 表单是否编辑过
  public edited = false;
  // 登录URL
  public loginUrl = '';
  public windowHeight = 0;
  // cache view
  public cacheViews: string[] = [];
  public routerBackName = '';
  public osList: any = null;
  public osNameList: string[] = [];
  public osMap: Dictionary = {};
  public installDefaultValues: Dictionary = {};
  public noticeShow = false;
  public AUTO_SELECT_INSTALL_CHANNEL = -1;

  // agent_package 显示开关
  public ENABLE_AGENT_PACKAGE_UI = false;
  /**
   * 更新状态
   *
   */
  @Mutation
  public setAgentPackageUI(switchStatus: boolean) {
    this.ENABLE_AGENT_PACKAGE_UI = switchStatus;
  }
  /**
   * 设置全局可视区域的 loading 是否显示
   *
   * @param {Object} state store state
   * @param {boolean} loading 是否显示 loading
   */
  @Mutation
  public setNmMainLoading(loading: boolean) {
    this.nmMainLoading = loading;
  }
  /**
   * 更新当前用户 StateUser
   *
   * @param {Object} state store state
   * @param {Object} user StateUser 对象
   */
  @Mutation
  public updateUser(user: any) {
    this.user = Object.assign({}, user);
  }
  /**
   * 更新当前一级导航信息
   * @param {Object} state
   * @param {String} name
   */
  @Mutation
  public updateCurrentNavName(name: string) {
    this.currentNavName = name;
  }
  /**
   * 更新二级导航激活菜单项
   * @param {Object} state
   * @param {String} name
   */
  @Mutation
  public updateSubMenuName({ name, parentName }: { name: string, parentName?: string }) {
    const index: number = this.navList.findIndex(item => item.name === this.currentNavName);
    const exitInChildren = this.navList[index]
      && this.navList[index].children?.some((item: ISubNavConfig) => item.name === name);
    if (exitInChildren) {
      this.navList[index].currentActive = name;
    } else if (parentName) {
      this.navList[index].currentActive = parentName;
    }
  }
  /**
   * 设置三级导航标题
   * @param {*} state
   * @param {*} title
   */
  @Mutation
  public setNavTitle(title: string) {
    this.currentNavTitle = title;
  }
  /**
   * 设置是否自定义导航内容
   * @param {*} state
   * @param {*} show
   */
  @Mutation
  public setCustomNavContent(show = false) {
    this.customNavContent = show;
  }
  /**
   * 到顶部返回的路由背景重置为白色
   * @param {*} state
   * @param {*} isDefault
   */
  @Mutation
  public setToggleDefaultContent(isDefault = false) {
    this.isDefaultContent = isDefault;
  }
  /**
   * 业务范围
   * @param {*} state
   * @param {*} list
   */
  @Mutation
  public setBkBizList(list: IBkBiz[] = []) {
    this.bkBizList = list;
  }
  /**
   * 云服务商
   * @param {*} state
   * @param {*} list
   */
  @Mutation
  public setIspList(list: IIsp[] = []) {
    this.ispList = list;
  }
  /**
   * 当前选中的业务范围
   * @param {*} state
   * @param {*} biz
   */
  @Mutation
  public setSelectedBiz(biz: number[] = []) {
    this.selectedBiz = biz;
    this.selectedBizName = biz.map(id => this.bkBizList.find(item => item.bk_biz_id === id)?.bk_biz_name);
  }
  @Mutation
  public setFont(list: ICheckItem[] = []) {
    Vue.set(this, 'fontList', list);
    const font = list.length ? list.find(item => item.checked) : false;
    if (font) {
      this.fontSize = font.id as string;
    }
  }
  /**
   * 当前语言类型
   * @param {String} StateLanguage
   */
  @Mutation
  public setLanguage(language: string) {
    this.language = language;
  }
  @Mutation
  public updatePermissionSwitch(permissionSwitch: boolean) {
    this.permissionSwitch = permissionSwitch;
  }
  /**
   * 更新业务的拉取权限类型
   */
  @Mutation
  public updateBizAction(action: string) {
    this.bizAction = action;
  }
  /**
   * 更新页面的查看权限
   */
  @Mutation
  public updatePagePermission(permission: boolean) {
    this.hasPagePermission = permission;
  }
  /**
   * 更新表单编辑状态
   */
  @Mutation
  public updateEdited(edited: boolean) {
    this.edited = edited;
  }
  /* 设置登录URL
   * @param {*} state
   * @param {*} url
   */
  @Mutation
  public setLoginUrl(url: string) {
    this.loginUrl = url;
  }

  @Mutation
  public  updateScreenInfo(height: number) {
    this.windowHeight = height;
  }

  /**
   * 添加缓存
   * @param view
   * @returns
   */
  @Mutation
  public addCachedViews(view: Route) {
    if (!view.name || this.cacheViews.includes(view.name)) return;

    this.cacheViews.push(view.name);
  }

  /**
   * 删除缓存
   * @param view
   * @returns
   */
  @Mutation
  public deleteCachedViews(view: Route) {
    if (!view.name) return;

    const index = this.cacheViews.indexOf(view.name);
    index > -1 && this.cacheViews.splice(index, 1);
  }

  /**
   * 删除指定name组件的路由缓存
   * @param name
   */
  @Mutation
  public deleteCachedViewsByName(name: string) {
    const index = this.cacheViews.indexOf(name);
    index > -1 && this.cacheViews.splice(index, 1);
  }
  /**
   * router-back mixins 返回指定组件名称
   * @param name
   */
  @Mutation
  public updateRouterBackName(name = '') {
    this.routerBackName = name;
  }
  @Mutation
  public updateOsList(list = []) {
    this.osList = list;
    this.osNameList = list.map(item => item.name);
    this.osMap = list.reduce((map, item) => {
      const { id = '', name = '' } = item;
      const osLower = id.toLowerCase();
      const osUpper = id.toUpperCase();
      map[id] = name;
      map[osLower] = name;
      map[osUpper] = name;
      return map;
    }, {});
  }
  @Mutation
  public updateInstallDefaultValues(config: Dictionary) {
    this.installDefaultValues = config;
  }
  @Mutation
  public updateNoticeShow(isShow: boolean) {
    this.noticeShow = isShow;
  }
  @Mutation
  public setAutoJudge(val: number) {
    this.AUTO_SELECT_INSTALL_CHANNEL = val;
  }

  /**
   * 获取用户信息
   *
   * @param {Object} context store 上下文对象 { commit, state, dispatch }
   *
   * @return {Promise} promise 对象
   */
  @Action
  public userInfo(context: any, config = {}) {
    // ajax 地址为 USER_INFO_URL，如果需要 mock，那么只需要在 url 后加上 AJAX_MOCK_PARAM 的参数，
    // 参数值为 mock/ajax 下的路径和文件名，然后加上 invoke 参数，参数值为 AJAX_MOCK_PARAM 参数指向的文件里的方法名
    // 例如本例子里，ajax 地址为 USER_INFO_URL，mock 地址为 USER_INFO_URL?AJAX_MOCK_PARAM=index&invoke=getUserInfo

    // 后端提供的地址
    // const url = USER_INFO_URL
    // mock 的地址，示例先使用 mock 地址
    const mockUrl = `${USER_INFO_UR
      + (USER_INFO_URL.indexOf('?') === -1 ? '?' : '&') + AJAX_MOCK_PARAM}=index&invoke=getUserInfo`;
    return http.get(mockUrl, {}, config).then((response) => {
      const userData = response.data || {};
      context.commit('updateUser', userData);
      return userData;
    });
  }
  /**
   * 获取业务范围列表
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getBkBizList(params: { action: string }) {
    const list = await retrieveBiz(params).catch(() => ([]));
    this.setBkBizList(list.map(item => ({
      ...item,
      action: params ? params.action : '',
      disabled: !item.has_permission,
    })));
    return list;
  }
  /**
   * 获取业务权限列表(权限接口是复用的业务列表接口，单独写是一个界面可能会发多次请求，但有些请求是不需要更新业务列表的)
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getBkBizPermission({ action,  updateBiz }: { action: string, updateBiz?: boolean }) {
    const list = await retrieveBiz({ action }).catch((err: any) => {
      if (axios.isCancel(err)) {
        return err; // 取消的请求需要自己处理
      }
      return [];
    });
    if (updateBiz && Array.isArray(list)) {
      this.setBkBizList(list.map(item => ({ ...item, action, disabled: !item.has_permission })));
    }
    return list;
  }
  /**
   * 云服务商列表
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getIspList() {
    const data = await retrieveGlobalSettings({
      key: 'isp',
    }).catch(() => ([]));
    this.setIspList(data.isp);
  }
  /**
   * 获取业务下的拓扑
   */
  @Action
  public async getBizTopo({ bk_biz_id }: { 'bk_biz_id': number }) {
    const res = await fetchTopo({ bk_biz_id }).catch(() => {});
    return res;
  }
  /**
   * 获取权限申请详情
   * @param { instance_id, instance_name } param
   */
  @Action
  public async getApplyPermission(param: IAuthApply) {
    const res = await fetchPermission(param).catch(() => ({
      apply_info: [],
      url: '',
    }));
    return res;
  }
  /**
   * 获取一些前置的权限类型
   * @param { pk } param
   */
  @Action
  public async getPagePermission(name: string) {
    return await permissionMethodsMap[name]().catch(() => ({}));
  }
  /**
   * get RSA public_key
   */
  @Action
  public async getPublicKey(params = { names: ['DEFAULT'] }): Promise<IKeyItem> {
    const data: IKeyItem[] = await fetchPublicKeys(params).catch(() => []);
    return data.find(item => item.name === 'DEFAULT') || {};
  }
  @Action
  public async getOsList(category = 'os_type'): Promise<Dictionary> {
    const res = await getFilterCondition({ category }).catch(() => []);
    return res || [];
  }

  /**
   * agent 安装默认配置
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getDefaultConfig() {
    const data = await retrieveGlobalSettings({ key: 'INSTALL_DEFAULT_VALUES' }).catch(() => ({}));
    const defaultPort = window.PROJECT_CONFIG.DEFAULT_SSH_PORT ? Number(window.PROJECT_CONFIG.DEFAULT_SSH_PORT) : 22;
    const defaultWinPort = 445;
    const config = data?.INSTALL_DEFAULT_VALUES || {};
    this.osNameList.map(name => name.toUpperCase()).forEach((name) => {
      const portConfig = { port: name === 'WINDOWS' ? defaultWinPort : defaultPort };
      if (config[name]) {
        config[name] = Object.assign(portConfig, config[name]);
      } else {
        config[name] = portConfig;
      }
    });
    this.updateInstallDefaultValues(config);
  }

  /**
   * 获取判断是否获取直连安装通道下拉选择数据的布尔字段AUTO_SELECT_INSTALL_CHANNEL_ONLY_DIRECT_AREA
   * @param {*} param
   */
  @Action
  public async getAutoJudgeInstallChannel() {
    const data = await retrieveGlobalSettings({ key: 'AUTO_SELECT_INSTALL_CHANNEL_ONLY_DIRECT_AREA' }).catch(() => ({}));
    const dataValue = data.AUTO_SELECT_INSTALL_CHANNEL_ONLY_DIRECT_AREA === undefined ? -1 : Number(data.AUTO_SELECT_INSTALL_CHANNEL_ONLY_DIRECT_AREA);
    this.setAutoJudge(dataValue);
  /**
   * agent_package 相关的显示开关配置
   */
  @Action
  public async getAgentPackageUI() {
    const { ENABLE_AGENT_PACKAGE_UI = false } = await getAgentPackageUI({ key: 'ENABLE_AGENT_PACKAGE_UI' }).catch(() => ({}));
    this.setAgentPackageUI(ENABLE_AGENT_PACKAGE_UI);
  }
}
