/* eslint-disable max-len */
import Vue from 'vue';
import { Module, VuexModule, Action, Mutation } from 'vuex-module-decorators';
import { listHost, listProcess } from '@/api/modules/plugin';
import {
  listPlugin,
  retrievePlugin,
  pluginHistory,
  pluginParse,
  createRegisterTask,
  queryRegisterTask,
  createExportPluginTask,
  queryExportPluginTask,
  packageStatusOperation, // 包历史 - 操作
  updatePlugin,
  pluginStatusOperation, // 插件包状态操作
  listPluginHost,
  fetchConfigVariables,
  operatePlugin,
  fetchPackageDeployInfo,
  fetchResourcePolicy,
  fetchResourcePolicyStatus,
  setResourcePolicy,
} from '@/api/modules/plugin_v2';
import {
  listPolicy,
  hostPolicy,
  fetchPolicyTopo,
  policyInfo,
  policyPreview,
  createPolicy,
  updatePolicy,
  fetchCommonVariable,
  updatePolicyInfo,
  upgradePreview,
  policyPreselection,
  policyOperate,
  migratePreview,
  rollbackPreview,
  fetchPolicyAbnormalInfo,
} from '@/api/modules/policy';
import { nodesAgentStatus, listHost as previewHost } from '@/api/modules/host_v2';
import { getFilterCondition } from '@/api/modules/meta';
import { serviceTemplate } from '@/api/modules/cmdb';
import { sort } from '@/common/util';
import { IPluginRuleParams, IStrategy, IPluginDetail, IPkVersionRow, IPkParseRow, IPolicyBase, IPluginTopo, IPreviewHost, ITarget, IPolicyOperate, IPluginRow } from '@/types/plugin/plugin-type';
import { ISearchItem } from '@/types';
import { grayRuleType,  policyRuleType, pluginOperate } from '@/views/plugin/operateConfig';

// eslint-disable-next-line new-cap
@Module({ name: 'pluginNew', namespaced: true })
export default class PluginStore extends VuexModule {
  public operateType = ''; // 流程的操作类型
  public strategyData: IStrategy = {};
  public strategyList: IPluginTopo[] = [];
  public hostsByBizRange: number[] = [];
  public hostsByScopeRange: Dictionary = null;
  public authorityMap: Dictionary = {};

  // 主策略
  public get isPolicyRule() {
    return policyRuleType.includes(this.operateType);
  }
  // 灰度策略
  public get isGrayRule() {
    return grayRuleType.includes(this.operateType);
  }
  // 手动操作插件
  public get isPluginRule() {
    return pluginOperate.includes(this.operateType);
  }
  public get isCreateType() {
    return /create/ig.test(this.operateType);
  }

  @Mutation
  public updateOperateType(type: string) {
    this.operateType = type;
  }
  @Mutation
  public setStrategyDataByKey({ key, value }: { key: string, value: any }) {
    this.strategyData[key] = value;
  }
  // 初始化流程数据
  @Mutation
  public setStrategyData(data?: IStrategy) {
    this.strategyData = data || {
      plugin_info: {
        id: '',
        name: '',
      },
      name: '',
      scope: {
        object_type: 'HOST', // 当前始终为 HOST
        node_type: 'TOPO',
        nodes: [],
      },
      steps: [], // 目前只能有一个插件，后端使用数组是为了扩展
      configs: [],
      params: [],
    };
  }
  @Mutation
  public setStrategyList({ type = 'list', data = [], name = '' }: { type: 'list' | 'item', data: IPluginTopo[], name?: string  }) {
    if (type === 'list') {
      this.strategyList = data.map(item => ({ ...item, children: [] }));
    } else {
      const node = this.strategyList.find(item => item.name === name);
      if (node) {
        node.children?.splice(0, 0, ...data);
      }
    }
  }
  @Mutation
  public updateAuthority(map: Dictionary = {}) {
    Object.keys(map).forEach((key) => {
      const value = map[key];
      if (Object.prototype.hasOwnProperty.call(this.authorityMap, key)) {
        this.authorityMap[key] = value;
      } else {
        Vue.set(this.authorityMap, key, value);
      }
    });
  }
  @Mutation
  public updateBizRange(bizList: number[] = []) {
    this.hostsByBizRange.splice(0, this.hostsByBizRange.length, ...bizList);
  }
  @Mutation
  public updateScopeRange(scope: any) {
    this.hostsByScopeRange = scope;
  }

  // 更新流程相关的数据、状态
  @Action
  public setStateOfStrategy(params: any) {
    if (params instanceof Array) {
      params.forEach((item: { key: keyof IStrategy, value: any }) => {
        this.setStrategyDataByKey(item);
      });
    } else {
      this.setStrategyDataByKey(params);
    }
  }
  /**
   * 获取节点列表
   */
  @Action
  public async getHostList(params: any) {
    const data = await listHost(params).catch(() => ({
      total: 0,
      list: [],
    }));
    return data;
  }
  /**
   * 获取节点详情
   */
  @Action
  public async getHostPolicy(params: any) {
    return await hostPolicy(params).catch(() => []);
  }
  /**
   * 获取插件列表
   * @param {*} param0
   * @param {*} pk
   */
  @Action
  public async getProcessList(pk: string): Promise<IPluginTopo[]> {
    let data = await listProcess(pk).catch(() => []);
    data = data.map(item => ({ ...item, key: item.id, id: item.name }));
    return data;
  }
  /**
   * 获取节点列表-筛选条件
   */
  @Action
  public async getFilterList(params: any = { category: 'plugin_host' }): Promise<ISearchItem[]> {
    let data = await getFilterCondition(params).catch(() => []);
    data = data.map((item: any) => {
      if (item.children && item.children.length) {
        item.multiable = true;
        item.children = item.children.filter((child: any) => `${child.id}` && `${child.name}`).map((child: any) => {
          child.checked = false;
          child.name = `${child.name}`;
          return child;
        });
      }
      if (item.id === 'bk_cloud_id') {
        item.showSearch = true;
        item.width = 180;
        item.align = 'right';
        item.children = sort(item.children, 'name');
      }
      return item;
    });
    return data;
  }
  // 插件操作
  @Action
  public async pluginOperate(params: any) {
    const result = await operatePlugin(params).catch(() => ({}));
    return result;
  }

  // 获取策略列表
  @Action
  public async getPluginRules(params: IPluginRuleParams): Promise<{ total: number, list: IPolicyBase[] }> {
    return await listPolicy(params).catch(() => ({ total: 0, list: [] }));
  }
  // 查询策略下主机插件安装失败的情况
  @Action
  public async getFetchPolicyAbnormalInfo(params: { 'policy_ids': number[] }): Promise<Dictionary> {
    return await fetchPolicyAbnormalInfo(params).catch(() => ({}));
  }

  @Action
  public async getPolicyInfo(pk: string | number) {
    const data = await policyInfo(pk).catch(() => ({ plugin_info: {}, scope: {} }));
    const { name, plugin_info, scope, steps = [{}] } = data;
    const [step] = steps;
    const configs = (step?.configs || []).map((item: any) => ({
      ...item,
      support_os_cpu: `${item.os} ${item.cpu_arch}`,
    }));
    return { ...data, name, plugin_info, scope, steps, configs, params: step?.params || [] };
  }
  // 策略拓扑
  @Action
  public async fetchPolicyTopo(params?: { 'plugin_name'?: string, keyword?: string }): Promise<IPluginTopo[]> {
    return await fetchPolicyTopo(params).catch(() => []);
  }
  // 执行预览
  @Action
  public async getTargetPreview(params: { conditions?: any[], page?: number, pagesize?: number }): Promise<{
    total: number
    list: IPreviewHost[]
    nodes: ITarget[]
    'agent_status_count': { [key: string]: number }
  }> {
    return await policyPreview(params).catch(() => ({ total: 0, list: [] }));
  }
  // 执行前置计算-预览
  @Action
  public async getMigratePreview(params: { conditions?: any[], page?: number, pagesize?: number }): Promise<any[]> {
    return await migratePreview(params).catch(() => ([]));
  }
  // 执行前置计算- 灰度删除回滚 -预览
  /**
   * @Params 同 v2/host/search/ 接口
  */
  @Action
  public async getRollbackPreview(params: { conditions?: any[], page?: number, pagesize?: number }): Promise<any> {
    return await rollbackPreview(params).catch(() => ({ total: 0, list: [] }));
  }
  // 执行预览 - 仅灰度删除查看agent异常的主机
  @Action
  public async  getAbnormalHost(param) {
    return await previewHost(param).catch(() => ({ total: 0, list: [] }));
  }
  // 统计给定拓扑节点的agent状态统计
  @Action
  public async getNodesAgentStatus(params: { nodes?: any[], page?: number, pagesize?: number }) {
    return await nodesAgentStatus(params).catch(() => ([]));
  }

  // 新建策略
  @Action
  public async createPolicy(params: any): Promise<IPolicyOperate> {
    return await createPolicy(params).catch(() => ({}));
  }
  // 更新策略
  @Action
  public async updatePolicy({ pk, params }: { pk: string, params: any }): Promise<IPolicyOperate> {
    return await updatePolicy(pk, params).catch(() => ({}));
  }
  // 更新策略信息
  @Action
  public async updatePolicyInfo({ pk, params }: { pk: string | number, params: any }) {
    return await updatePolicyInfo(pk, params).catch(() => ({}));
  }
  // 策略操作 - 停用、启用、删除、卸载并删除
  @Action
  public async operatePolicy(params: Dictionary) {
    return await policyOperate(params).catch(() => ({}));
  }
  // 插件版本配置列表
  @Action
  public async pkConfigList(pk: number) {
    return await upgradePreview(pk).catch(() => []);
  }
  // 获取配置模板参数
  @Action
  public async getConfigVariables(params: { 'config_tpl_ids': number[] }) {
    return await fetchConfigVariables(params).catch(() => ([]));
  }
  // 获取公共变量
  @Action
  public async variableList() {
    return await fetchCommonVariable().catch(() => ({ linux: [], windows: [] }));
  }

  // 插件包列表
  @Action
  public async pluginPkgList(params: {
    search?: string
    'simple_all'?: boolean
    page?: number
    pagesize?: number
  }): Promise<{ total: number, list: IPluginRow[] }> {
    return await listPlugin(params).catch(() => ({ total: 0, list: [] }));
  }

  // 懒加载 插件包列表 节点数量
  @Action
  public async pluginPkgNodeNum(params: Dictionary): Promise<Dictionary> {
    return await fetchPackageDeployInfo(params).catch(() => ({}));
  }

  // 更新插件包别名
  @Action
  public async updatePluginAlias({ pk, params }: { pk: string | number, params: { description: string } }) {
    return await updatePlugin(pk, params);
  }

  // 查询插件所包含的目标
  @Action
  public async getPluginTargetList(params: Dictionary) {
    return await listPluginHost(params).catch(() => ({ total: 0, list: [] }));
  }

  // 插件状态操作
  @Action
  public async pluginStatusOperation(params: { id: number[], operation: string }) {
    return await pluginStatusOperation(params).catch(() => ([]));
    //
  }

  // 插件包详情
  @Action
  public async pluginDetail(pk: any): Promise<IPluginDetail> {
    const data = await retrievePlugin(pk).catch(() => ({ plugin_packages: [] }));
    return data;
  }

  // 带预选的插件包详情
  @Action
  public async pluginSelectionDetail(params: any) {
    const data = await policyPreselection(params).catch(() => ({ plugin_packages: [] }));
    return data;
  }

  // 插件包详情 - 下载 // 触发打包导出任务
  @Action
  public async pluginDownload(params: { category: string, 'query_params': any }) {
    const data = await createExportPluginTask(params).catch(() => ({}));
    return data;
  }
  // 插件包详情 - 轮询得到 下载的URL
  @Action
  public async getDownloadUrl(params: { 'job_id': number }) {
    const data = await queryExportPluginTask(params).catch(() => ({}));
    return data;
  }

  // 插件包版本历史
  @Action
  public async versionHistory({ pk, params }: { pk: string | number, params: any }): Promise<IPkVersionRow[]> {
    const data = await pluginHistory(pk, params).catch(() => []);
    return data.map((row: any) => {
      const mainConfig = row.config_templates?.find((item: any) => item.is_main);
      row.mainConfigVersion = mainConfig?.version || '--';
      row.childConfigTemplates = row.config_templates?.filter((item: any) => !item.is_main);
      row.operateLoading = false;
      row.support_os_cpu = `${row.os} ${row.cpu_arch}`;
      return row;
    });
  }

  // 插件包版本历史 - 操作
  @Action
  public async packageOperation(params: { operation: string }) {
    const data = await packageStatusOperation(params).catch(() => []);
    return data;
  }

  // 插件包解析
  @Action
  public async packageParse(params: { 'file_name': string, 'is_update'?: boolean, project?: string }): Promise<IPkParseRow[]> {
    const data = await pluginParse(params).catch(() => []);
    return data;
  }
  // 插件包导入
  @Action
  public async pluginPkgImport(params: { 'file_name': string, 'select_pkg_abs_paths': string[]}) {
    const result = await createRegisterTask(params).catch(() => false);
    return result;
  }

  // 查询插件包注册任务
  @Action
  public async getRegisterTask(params: { 'job_id': string }) {
    return await queryRegisterTask(params).catch(() => ({ status: 'failed' }));
  }

  // 查询业务下的资源树结构（单业务）
  @Action
  public async getTemplatesByBiz({ bk_biz_id }: { bk_biz_id: number }) {
    const res = await serviceTemplate({ bk_biz_id }).catch(() => []);
    return res.map(item => ({
      ...item,
      bk_inst_id: item.id,
      bk_inst_name: item.name,
      bk_obj_id: 'template',
    }));
  }

  // 查询资源策略信息
  @Action
  public async fetchResourcePolicy(params: { bk_biz_id: number, bk_obj_id: string, bk_inst_id?: number }) {
    const res = await fetchResourcePolicy(params).catch(() => ({ resource_policy: [] }));
    res.resource_policy = res.resource_policy.map(({ statistics = {}, ...item }) => ({
      ...item,
      total: statistics.total_count || 0,
      running: statistics.running_count || 0,
      terminated: statistics.terminated_count || 0,
    }));
    return res;
  }
  // 查询资源策略状态
  @Action
  public async fetchResourcePolicyStatus(params: { bk_biz_id: number, bk_obj_id: 'service_template' }) {
    return await fetchResourcePolicyStatus(params).catch(() => []);
  }
  // 更新
  @Action
  public async updateResourcePolicy(param) {
    return await setResourcePolicy(param).catch(() => ({ job_id_list: [] }));
  }
}
