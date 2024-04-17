import { VuexModule, Module, Action, Mutation } from 'vuex-module-decorators';
import { listCloud, deleteCloud, createCloud, retrieveCloud, updateCloud } from '@/api/modules/cloud';
import { retrieveCloudProxies, updateHost, removeHost } from '@/api/modules/host';
import { listAp } from '@/api/modules/ap';
import { installJob, operateJob } from '@/api/modules/job';
import { listCloudPermission } from '@/api/modules/permission';
import {
  createInstallChannel, deleteInstallChannel,
  listInstallChannel, updateInstallChannel,
} from '@/api/modules/installchannel';
import { transformDataKey } from '@/common/util';
import { ICloud, ICloudAuth, ICloudForm, ICloudSource, IProxyDetail, IChannel } from '@/types/cloud/cloud';
import { IAp } from '@/types/config/config';
import axios from 'axios';

export const SET_CLOUD_AP = 'SET_CLOUD_AP';
export const SET_CLOUD_LIST = 'SET_CLOUD_LIST';
export const UPDATE_AP_URL = 'updateApUrl';
// eslint-disable-next-line new-cap
@Module({ name: 'cloud', namespaced: true })
export default class CloudStore extends VuexModule {
  public apData: IAp[] = []; // 接入点
  public list: any[] = []; // 管控区域列表
  public url = ''; // 接入点Url
  public authorityMap: ICloudAuth = {};
  public channelServerKeys = ['btfileserver', 'dataserver', 'taskserver'];

  public get apList() {
    return this.apData;
  }
  public get cloudList() {
    return this.list;
  }
  public get apUrl() {
    return this.url;
  }
  public get authority() {
    return this.authorityMap;
  }

  // 接入点数据
  @Mutation
  public [SET_CLOUD_AP](data = []) {
    this.apData = data;
  }
  @Mutation
  public [SET_CLOUD_LIST](data: ICloud[] = []) {
    this.list = data;
  }
  @Mutation
  public [UPDATE_AP_URL](apUrl = '') {
    this.url = apUrl;
  }
  @Mutation
  public setAuthority(map: ICloudAuth = {}) {
    this.authorityMap = map;
  }

  /**
    * 获取管控区域列表
    * @param {s} param0
    * @param {*} params
    */
  @Action
  public async getCloudList(params?: { 'bk_biz_scope'?: number[] }): Promise<ICloud[]> {
    let data = await listCloud(params)
      .then((res: ICloudSource[]) => res.map(item => Object.assign(item, item.permissions)))
      .catch(() => []);
    // 排序 未安装 --> 异常 --> 正常
    data = (transformDataKey(data) as ICloud[]).sort((pre, next) => {
      if (!pre.proxyCount || !next.proxyCount) {
        return pre.proxyCount - next.proxyCount;
      }
      return Number(pre.exception !== 'abnormal') - Number(next.exception !== 'abnormal');
    });
    this[SET_CLOUD_LIST](data);
    return data;
  }
  /**
   * 获取接入点
   */
  @Action
  public async getApList(): Promise<IAp[]> {
    const data = await listAp().catch(() => []);
    this[SET_CLOUD_AP](data);
    return data;
  }
  /**
   * 获取管控区域详情
   * @param {*} pk
   */
  @Action
  public async getCloudDetail(pk: string): Promise<ICloud> {
    const data = await retrieveCloud(pk).catch(() => ({}));
    return transformDataKey(data) as ICloud;
  }
  /**
   * 删除管控区域
   * @param {*} params
   */
  @Action
  public async deleteCloud(params: number): Promise<boolean> {
    const data = await deleteCloud(params, null, { needRes: true }).catch(() => false);
    return data;
  }
  /**
   * 创建管控区域
   * @param {*} params
   */
  @Action
  public async createCloud(params: ICloudForm) {
    const data = await createCloud(params).catch(() => false);
    return data;
  }
  /**
   * 安装Proxy
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async setupProxy({ params, config }: any) {
    const data = installJob(params, config).catch(() => false);
    return data;
  }
  /**
   * 更新管控区域
   * @param {*} commit
   * @param {*} pk
   * @param {*} params
   */
  @Action
  public async updateCloud({ pk, params }: { pk: number, params: ICloudForm }) {
    const data = await updateCloud(pk, params).then(() => true)
      .catch(() => false);
    return data;
  }
  /**
   * 获取管控区域Proxy列表
   * @param {*} param0
   * @param {*} pk
   */
  @Action
  public async getCloudProxyList(params: { 'bk_cloud_id': number }): Promise<IProxyDetail[]> {
    let data = await retrieveCloudProxies(params).catch(() => []);
    data = data.map((item: IProxyDetail) => {
      const {
        bt_speed_limit = '',
        data_path = '',
        peer_exchange_switch_for_agent = false,
        ...extraOther
      } = item.extra_data || {};
      return {
        ...item,
        status: item.status ? item.status.toLowerCase() : '',
        bt_speed_limit,
        data_path,
        peer_exchange_switch_for_agent: !!peer_exchange_switch_for_agent,
        ...extraOther,
      };
    });
    return data;
  }
  /**
   * 更新主机信息
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async updateHost(params: any) {
    let isCatch = false;
    const data = await updateHost(params).catch(() => {
      isCatch = true;
      return false;
    });
    return isCatch ? data : true;
  }
  /**
   * Proxy 重启 下线 卸载操作
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async operateJob(params: { 'job_type': string, 'bk_host_id': number[], agent_setup_info?: {} }): Promise<{ 'job_id'?: number }> {
    const data = await operateJob(params).catch(() => false);
    return data;
  }
  /**
   * 移除Proxy
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async removeHost(params: { 'is_proxy': boolean, 'bk_host_id': number[] }) {
    const data = await removeHost(params).catch(() => false);
    return data;
  }
  /**
   * 获取服务信息
   * @param {*} param0
   * @param {*} params
   */
  // public async getServiceInfo(params) {
  //   const data = await serviceInfo(params).catch(() => ({}))
  //   return data
  // }
  /**
   * 安装proxy时获取ap的URL
   * @param {id} ap的id
   * @param {urlType} 节点需要的url类型
   */
  @Action
  public setApUrl({ id, urlType = 'package_outer_url' }: any) {
    let apUrl = '';
    if (!id && id !== 0) {
      this[UPDATE_AP_URL]();
      return;
    }
    const filterAp = id === -1
      ? this.apData.filter(item => item.id !== -1) : this.apData.filter(item => item.id === id);
    if (filterAp.length) {
      apUrl = filterAp.map(item => item[urlType as 'package_outer_url']).join(', ');
    }
    this[UPDATE_AP_URL](apUrl);
  }
  /**
   * 获取操作权限
   */
  @Action
  public async getCloudPermission() {
    const res = await listCloudPermission().catch((err: any) => {
      if (axios.isCancel(err)) {
        return err;
      }
      return {
        edit_action: [],
        delete_action: [],
        create_action: false,
        view_action: [],
      };
    });
    return res;
  }

  // 安装通道相关
  @Action
  public async createChannel(params: any): Promise<IChannel> {
    return await createInstallChannel(params).catch(() => ({}));
  }
  @Action
  public async deleteChannel({ id, params }: { id: number, params: { 'bk_cloud_id': number }}) {
    return await deleteInstallChannel(id, { data: params }, { hasBody: true }).catch(() => false);
  }
  @Action
  public async getChannelList(params?: { 'bk_cloud_id': number }) {
    const list = await listInstallChannel(params).catch(() => []);
    const defaultChannel = { id: 'default', name: window.i18n.t('默认通道') };
    this.store.commit('agent/setChannelList', [defaultChannel, ...list]);
    return list;
  }
  @Action
  public async updateChannel({ id, params }: { id: number, params: Dictionary }) {
    return await updateInstallChannel(id, params).catch(() => false);
  }
}
