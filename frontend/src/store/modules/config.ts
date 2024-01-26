import Vue from 'vue';
import { VuexModule, Module, Action, Mutation } from 'vuex-module-decorators';
import { ITaskConfig, IAvailable, IApExpand, IApParams, IAp } from '@/types/config/config';

import { transformDataKey } from '@/common/util';
import { apIsUsing, listAp, retrieveAp, createAp, updateAp, testAp, deleteAp } from '@/api/modules/ap';
import { retrieveGlobalSettings, jobSettings } from '@/api/modules/meta';
import { listApPermission } from '@/api/modules/permission';
import { healthz } from '@/api/modules/healthz';
// import { initIpProp } from '@/setup/ipv6';

// eslint-disable-next-line new-cap
@Module({ name: 'config', namespaced: true })
export default class ConfigStore extends VuexModule {
  public pageLoading = true;
  public apDetail!: IApParams = {};
  public healthzData: any[] = [];
  public selectedIPs: string[] = [];
  public allIPs: string[] = [];
  // 'cmdb', 'job', 'bk_data', 'metadata', 'nodeman', 'gse', 'rabbitmq', 'saas_celery'
  public saasDependenciesComponent: string[] = [];

  public get loading() {
    return this.pageLoading;
  }
  public get detail() {
    return this.apDetail || {};
  }

  @Mutation
  public resetDetail() {
    this.apDetail = {
      name: '',
      region_id: '',
      city_id: '',
      zk_account: '',
      zk_password: '',
      pwsFill: false,
      zk_hosts: [
        { zk_ip: '', zk_port: '' },
      ],
      btfileserver: {
        inner_ip_infos: [{ ip: '' }],
        outer_ip_infos: [{ ip: '' }],
      },
      dataserver: {
        inner_ip_infos: [{ ip: '' }],
        outer_ip_infos: [{ ip: '' }],
      },
      taskserver: {
        inner_ip_infos: [{ ip: '' }],
        outer_ip_infos: [{ ip: '' }],
      },
      callback_url: '',
      outer_callback_url: '',
      package_inner_url: '',
      package_outer_url: '',
      agent_config: {
        linux: {},
        windows: {},
      },
      nginx_path: '',
      description: '',
      proxy_package: [],
    };
  }
  @Mutation
  public updateDetail(detail: { [key: string]: any }) {
    Object.keys(detail).forEach((key: string) => {
      // if (Object.prototype.hasOwnProperty.call(this.apDetail, key)) {
      //   this.apDetail[`${key}`] = detail[key]
      // } else {
      if (['btfileserver', 'dataserver', 'taskserver'].includes(key)) {
        Vue.set(this.apDetail, key, { ...detail[key] });
        // Vue.set(this.apDetail, key, detail[key].map((server) => {
        //   const copyServer = { ...server };
        //   initIpProp(copyServer, ['inner_ip', 'outer_ip']);
        //   return copyServer;
        // }));
      } else {
        Vue.set(this.apDetail, key, detail[key]);
      }
      // }
    });
  }
  @Mutation
  public updateLoading(isLoading: boolean) {
    this.pageLoading = isLoading;
  }
  @Mutation
  public updateHealthzData(data: any[] = []) {
    this.healthzData.splice(0, this.healthzData.length, ...data);
  }
  @Mutation
  public updateSelectedIPs(data?: string[] = []) {
    this.selectedIPs.splice(0, this.selectedIPs.length, ...data);
  }
  @Mutation
  public updateAllIPs(data?: string[] = []) {
    this.allIPs.splice(0, this.allIPs.length, ...data);
  }
  @Mutation
  public updateSaasComponents(components?: string[] = []) {
    this.saasDependenciesComponent.splice(0, this.saasDependenciesComponent.length, ...components);
  }

  // 获取接入点列表
  @Action
  public async requestAccessPointList() {
    const data: IApExpand[] = await listAp()
      .then((res: IAp[]) => res.map(item => Object.assign(item, item.permissions)))
      .catch(() => []);
    data.forEach((row: IApExpand, index: number) => {
      row.collapse = !index;
      row.zk_hosts = row.zk_hosts || [];
      row.BtfileServer = row.btfileserver || [];
      row.DataServer = row.dataserver || [];
      row.TaskServer = row.taskserver || [];
    });
    return data;
  }
  // 获取接入点是否被使用
  @Action
  public async requestAccessPointIsUsing(): Promise<number[]> {
    return await apIsUsing().catch(() => ([]));
  }
  // 获取接入点详情
  @Action({ rawError: true })
  public async getGseDetail({ pointId }: { pointId: number | string }) {
    this.updateLoading(true);
    const data = await retrieveAp(pointId).catch(() => ({}));
    this.updateDetail(data);
    Vue.set(this.apDetail, 'pwsFill', !!data.zk_account);
    this.updateLoading(false);
    return data;
  }
  // 创建接入点
  @Action
  public async requestCreatePoint(params: IApParams) {
    const data = await createAp(params).catch(() => {});
    return data;
  }
  // 修改接入点
  @Action
  public async requestEditPoint({ pointId, data }: { pointId: number, data: IApParams }) {
    const result = await updateAp(pointId, data).catch(() => {});
    return result;
  }
  // 删除接入点
  @Action
  public async requestDeletetPoint({ pointId }: { pointId: number }) {
    const data = await deleteAp(pointId, null, { needRes: true }).catch(() => {});
    return data;
  }
  // 检查servers的可用性
  @Action
  public async requestCheckUsability(params: IAvailable) {
    const data = await testAp(params).catch(() => ({
      test_result: false,
      test_logs: [],
    }));
    return data;
  }
  // 拉取任务配置参数
  @Action
  public async requestGlobalSettings() {
    const data = await retrieveGlobalSettings({
      key: 'job_settings',
    }).catch(() => ({ jobSettings: {} }));
    return transformDataKey(data);
  }
  // 保存任务配置参数
  @Action
  public async saveGlobalSettings(params: ITaskConfig): Promise<{ result: boolean }> {
    return await jobSettings(params, { needRes: true }).catch(() => ({}));
  }
  /**
   * 获取操作权限
   */
  @Action
  public async getApPermission(): Promise<{ 'edit_action': any[], 'delete_action': any[], 'create_action': boolean }> {
    return await listApPermission().catch(() => ({
      edit_action: [],
      delete_action: [],
      create_action: false,
    }));
  }

  /**
   * 自监控
   */
  @Action
  public async getHealthz(): Promise<any> {
    return await healthz().catch(() => []);
  }
}

