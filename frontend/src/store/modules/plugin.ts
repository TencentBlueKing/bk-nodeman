import { Module, VuexModule, Action } from 'vuex-module-decorators';
import { listHost, listProcess, listPackage, operatePlugin } from '@/api/modules/plugin';
import { getFilterCondition } from '@/api/modules/meta';
import { sort } from '@/common/util';

// eslint-disable-next-line new-cap
@Module({ name: 'pluginOld', namespaced: true })
export default class PluginOldStore extends VuexModule {
  /**
  * 获取主机列表
  * @param {*} param0
  * @param {*} params
  */
  @Action
  public async getHostList(params: any) {
    const data = await listHost(params).catch(() => ({
      total: 0,
      list: [],
    }));
    data.list = data.list.map((item: any) => {
      item.status = item.status ? item.status.toLowerCase() : 'unknown';
      item.version = item.version ? item.version : '--';
      item.job_result = item.job_result ? item.job_result : {};
      item.topology = item.topology && item.topology.length ? item.topology : [];
      return item;
    });
    return data;
  }
  /**
   * 获取筛选条件
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async getFilterCondition(category = 'plugin') {
    let data = await getFilterCondition({ category }).catch(() => []);
    data = data.map((item: any) => {
      if (item.children && item.children.length) {
        item.multiable = true;
        item.children = item.children.filter((child: any) => (`${child.id}`) && (`${child.name}`)).map((child: any) => {
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
  /**
   * 获取插件列表
   * @param {*} param0
   * @param {*} pk
   */
  @Action
  public async getProcessList(pk: string) {
    const data = await listProcess(pk).catch(() => []);
    return data;
  }
  /**
   * 插件包列表
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async listPackage(params: any) {
    const data = await listPackage(params.pk, params.data).catch(() => []);
    return data;
  }
  /**
   * 插件操作
   * @param {*} param0
   * @param {*} params
   */
  @Action
  public async operatePlugin(params: any) {
    const data = await operatePlugin(params).catch(() => false);
    return data;
  }
}
