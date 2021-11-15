import { VuexModule, Module, Action, Mutation } from 'vuex-module-decorators';

import { listHost, removeHost } from '@/api/modules/host';
import { installJob, operateJob } from '@/api/modules/job';
import { listAp } from '@/api/modules/ap';
import { listCloud } from '@/api/modules/cloud';
import { getFilterCondition } from '@/api/modules/meta';
import { fetchPwd } from '@/api/modules/tjj';
import { sort } from '@/common/util';
import { ISearchChild, ISearchItem } from '@/types';
import { IAgentSearch, IAgentSearchIp, IAgentJob, IAgentHost } from '@/types/agent/agent-type';
import { IAp } from '@/types/config/config';
import { IChannel, ICloudSource } from '@/types/cloud/cloud';

export const SET_AP_LIST = 'setApList';
export const SET_CLOUD_LIST = 'setCloudList';
export const SET_CHANNEL_LIST = 'setChannelList';
export const UPDATE_AP_URL = 'updateApUrl';

// eslint-disable-next-line new-cap
@Module({ name: 'agent', namespaced: true })
export default class AgentStore extends VuexModule {
  public apList: IAp[] = [];
  public cloudList: ICloudSource[] = [];
  public channelList: IChannel[] = [];
  public apUrl = '';

  @Mutation
  public [SET_CLOUD_LIST](data: ICloudSource[] = []) {
    this.cloudList = data;
  }
  @Mutation
  public [SET_AP_LIST](data: IAp[] = []) {
    this.apList = data;
  }
  @Mutation
  public [SET_CHANNEL_LIST](data: IChannel = []) {
    this.channelList = data;
  }
  @Mutation
  public [UPDATE_AP_URL](apUrl = '') {
    this.apUrl = apUrl;
  }

  /**
   * 获取主机列表
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getHostList(params: IAgentSearch) {
    const data = await listHost(params).catch(() => ({
      total: 0,
      list: [],
      isFaied: true,
    }));
    data.list = data.list.map((item: IAgentHost) => {
      const {
        bt_speed_limit: btSpeedLimit,
        peer_exchange_switch_for_agent: peerExchangeSwitchForAgent = 1,
      } = item.extra_data || {};
      item.status = item.status ? item.status.toLowerCase() : 'unknown';
      item.version = item.version ? item.version : '--';
      item.job_result = item.job_result ? item.job_result : {} as any;
      item.topology = item.topology && item.topology.length ? item.topology : [];
      item.bt_speed_limit = btSpeedLimit || '';
      item.peer_exchange_switch_for_agent = !!peerExchangeSwitchForAgent || false;
      return item;
    });
    return data;
  }
  /**
   * 获取运行主机数量
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getRunningHost(params: IAgentSearch) {
    const data = await listHost(params).catch(() => ({
      running_count: 0,
      no_permission_count: 0,
    }));
    return data;
  }
  /**
   * 获取主机IP信息
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getHostIp(params: IAgentSearchIp) {
    const data = await listHost(params).catch(() => ({
      total: 0,
      list: [],
    }));
    return data;
  }
  /**
   * Agent相关安装
   */
  @Action
  public async installAgentJob({ params, config = {} }: {
    params: IAgentJob,
    config: { needRes?: boolean, globalError?: boolean }
  }) {
    const data = await installJob(params, config).catch(() => false);
    return data;
  }
  /**
   * 获取接入点
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getApList(autoSelect = true) {
    const data = await listAp().catch(() => []);
    // 编辑态且只有一个接入点时，不显示自动选择
    if (window.PROJECT_CONFIG.BKAPP_RUN_ENV !== 'ce' && (autoSelect || data.length > 1)) {
      data.unshift({
        id: -1,
        name: window.i18n.t('自动选择'),
      });
    }
    this[SET_AP_LIST](data);
    return data;
  }
  /**
   * 获取云区域列表
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getCloudList(params: { RUN_VER?: string } = {}) {
    // 权限中心模式 - 接口输出直连区域
    const isIam = window.PROJECT_CONFIG.USE_IAM === 'True';
    if (isIam) {
      Object.assign(params, { with_default_area: true });
    }
    let data: ICloudSource[] = await listCloud(params)
      .then((res: ICloudSource[]) => res.map(item => Object.assign(item, item.permissions)))
      .catch(() => []);
    // RUN_VER 非接口字段：ieod环境 添加 或 excel导入剔除直连区域
    if (isIam) {
      data.sort((a, b) => Number(b.view) - Number(a.view));
      if (params && params.RUN_VER === 'ieod') {
        data = data.filter(item => item.bk_cloud_id !== window.PROJECT_CONFIG.DEFAULT_CLOUD);
      }
    }
    if (!isIam && (!params || params.RUN_VER !== 'ieod')) {
      const defaultCloud = {
        bk_cloud_id: window.PROJECT_CONFIG.DEFAULT_CLOUD as number,
        bk_cloud_name: window.i18n.t('直连区域'),
      };
      data.unshift(defaultCloud as ICloudSource);
    }
    this[SET_CLOUD_LIST](data);
    return data;
  }
  /**
   * 获取筛选条件
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getFilterCondition(category = 'host') {
    let data: ISearchItem[] = await getFilterCondition({ category }).catch(() => []);
    data = data.map((item) => {
      if (item.children && item.children.length) {
        item.multiable = true;
        item.children = item.children.filter(child => (`${child.id}`)
        && (`${child.name}`)).map((child: ISearchChild) => {
          child.checked = false;
          child.name = `${child.name}`;
          return child;
        });
      }
      if (item.id === 'bk_cloud_id') {
        item.showSearch = true;
        item.width = 180;
        item.align = 'right';
        item.children = sort(item.children as ISearchChild[], 'name');
      }
      return item;
    });
    return data;
  }
  /**
   * 移除Host
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async removeHost(params: IAgentJob) {
    const data = await removeHost(params).catch(() => false);
    return data;
  }
  /**
   * 重启、卸载 主机
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async operateJob(params: IAgentJob) {
    const data = await operateJob(params).catch(() => false);
    return data;
  }
  /**
   * 主机是否可用铁将军
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async fetchPwd(params: any) {
    const data = await fetchPwd(params).catch(() => false);
    return data;
  }
  @Action
  public setApUrl({ id, urlType = 'package_outer_url' }: { id: number | string, urlType: string }) {
    let apUrl = '';
    if (!id && id !== 0) {
      this[UPDATE_AP_URL]();
      return;
    }
    const filterAp = id === -1
      ? this.apList.filter(item => item.id !== -1)
      : this.apList.filter(item => item.id === id);
    if (filterAp.length) {
      apUrl = filterAp.map((item: any) => item[urlType]).join(', ');
    }
    this[UPDATE_AP_URL](apUrl);
  }
}
