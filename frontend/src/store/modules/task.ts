import { VuexModule, Module, Action, Mutation } from 'vuex-module-decorators';
import {
  listJob, // 任务列表
  retrieveJob, // 任务详情 & 主机列表
  getJobLog, // 查询日志
  retryJob, // 重试
  retryNode, // 原子重试
  revokeJob, // 终止
  collectJobLog, // 日志上报
  getJobCommands, // 获取手动安装命令
} from '@/api/modules/job';
import { getFilterCondition } from '@/api/modules/meta';
import { transformDataKey, sort } from '@/common/util';
import { ITaskParams, IHistory, ITask, ITaskHost } from '@/types/task/task';
import { ISearchChild, ISearchItem } from '@/types';

interface IJob {
  jobId: number
  params: ITaskParams,
  canceled?: boolean
}

// eslint-disable-next-line new-cap
@Module({ name: 'task', namespaced: true }) // 命名冲突、调用两次
export default class TaskStore extends VuexModule {
  public routetParent = '';

  @Mutation
  public setRouterParent(name: string) {
    this.routetParent = name;
  }
  // 历史任务列表
  @Action
  public async requestHistoryTaskList(params: ITaskParams) {
    const data = await listJob(params).catch(() => ({
      total: 0,
      list: [],
      filterCondition: [],
    }));
    data.list.forEach((row: ITaskHost) => {
      row.status = row.status.toLowerCase();
    });
    return transformDataKey(data) as { total: number, list: IHistory[] };
  }
  // 单个任务详情, 包含主机列表
  @Action
  public async requestHistoryTaskDetail({ jobId, params, canceled = false }: IJob) {
    const res: ITask = await retrieveJob(jobId, params).catch(() => {});
    if (res) {
      res.list.forEach((row: ITaskHost) => {
        if (row.bk_cloud_id === 0 || row.bk_cloud_name === 'default area') {
          row.bk_cloud_name = window.i18n.t('直连区域');
        }
        row.status = row.status.toLowerCase();
      });
      return transformDataKey(res);
    }
    return canceled ? { canceled: true } : false;
  }
  // 主机日志详情
  @Action
  public async requestHistoryHostLog({ jobId, params }: IJob) {
    const data = await getJobLog(jobId, params).catch(() => {});
    if (data) {
      data.forEach((row: ITaskHost) => {
        row.status = row.status.toLowerCase();
      });
    }
    return data;
  }
  // 任务重试
  @Action
  public async requestTaskRetry({ jobId, params }: IJob) {
    const data = await retryJob(jobId, params, { needRes: true }).catch(() => ({}));
    return data;
  }
  // 任务终止
  @Action
  public async requestTaskStop({ jobId, params }: IJob) {
    const res = await revokeJob(jobId, params, { needRes: true }).catch(() => ({}));
    return res;
  }
  // 原子重试
  @Action
  public async requestNodeRetry({ jobId, params }: IJob) {
    const res = await retryNode(jobId, params, { needRes: true }).catch(() => ({}));
    return res;
  }
  // 获取筛选条件
  @Action
  public async getFilterList(params: Dictionary = { category: 'job' }) {
    const data = await getFilterCondition(params).then((res: ISearchItem[]) => {
      const userName = window.PROJECT_CONFIG ? window.PROJECT_CONFIG.USERNAME || '' : '';
      const list = res.map((item: ISearchItem) => {
        item.multiable = true;
        if (item.id === 'job_type' && Array.isArray(item.children)) {
          const sortAgent: ISearchChild[] = [];
          const sortProxy: ISearchChild[] = [];
          const sortPlugin: ISearchChild[] = [];
          const sortOther: ISearchChild[] = [];
          item.children.forEach((item: ISearchChild) => {
            if (/agent/ig.test(item.id)) {
              sortAgent.push(item);
            } else if (/proxy/ig.test(item.id)) {
              sortProxy.push(item);
            } else if (/plug/ig.test(item.id)) {
              sortPlugin.push(item);
            } else {
              sortOther.push(item);
            }
          });
          item.children = (sort(sortAgent, 'name') || []).concat(
            sort(sortProxy, 'name') || [],
            sort(sortPlugin, 'name') || [],
            sort(sortOther, 'name') || [],
          );
        }
        if (userName && item.id === 'created_by' && item.children && item.children.length) {
          item.children.forEach((item) => {
            if (item.id === userName) {
              item.name = window.i18n.t('我');
            }
          });
        }
        if (item.children && item.children.length) {
          item.children = item.children.map((child) => {
            child.checked = false;
            return child;
          });
        }
        return item;
      });
      return list;
    })
      .catch(() => []);
    return data;
  }
  // 日志上报
  @Action
  public async requestReportLog({ jobId, params }: IJob) {
    const data = await collectJobLog(jobId, params).catch(() => {});
    return data;
  }
  @Action
  public async requestCommands({ jobId, params }: { jobId: number, params: { 'bk_host_id': number } }) {
    const data = await getJobCommands(jobId, params).catch(() => null);
    return transformDataKey(data);
  }
}
