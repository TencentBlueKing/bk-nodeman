import { Vue, Component } from 'vue-property-decorator';
import { MainStore } from '@/store/index';
import { IFilterDialogRow } from '@/types/agent/agent-type';

@Component

export default class FilterIpMixin extends Vue {
  // 过滤ip列表
  public filterList: IFilterDialogRow[] = [];
  // 是否显示过滤提示
  public showFilterTips = false;
  // ip过滤对话框
  public showFilterDialog = false;
  /**
   * 处理过滤IP信息
   */
  public handleFilterIp(result: { 'job_id'?: number, 'ip_filter': IFilterDialogRow[] }, isInstall?: boolean) {
    if (result) {
      if (result.job_id) {
        const router = {
          name: 'taskDetail',
          params: { taskId: result.job_id, routerBackName: 'taskList' },
        };
        MainStore.updateEdited(false);
        // this.handleShowFilterMsg(result.ip_filter)
        isInstall ? this.$router.push(router)
          : this.$router.replace(router);
      } else {
        this.handleShowMsg(result.ip_filter);
      }
    }
  }
  /**
   * 部分过滤提示
   */
  public handleShowFilterMsg(data: IFilterDialogRow[] = []) {
    if (!data || !data.length) return;
    this.$bkMessage({
      theme: 'warning',
      message: this.$t('部分过滤提示', { firstIp: data[0].ip, total: data.length }),
    });
  }
  /**
   * 全部过滤错误提示
   */
  public handleShowMsg(data: IFilterDialogRow[]) {
    this.filterList = data;
    const h = this.$createElement;
    this.$bkMessage({
      theme: 'error',
      message: h('p', [
        window.i18n.t('全部过滤提示'),
        h('span', {
          style: {
            color: '#3A84FF',
            cursor: 'pointer',
          },
          on: {
            click: this.handleShowDetail,
          },
        }, window.i18n.t('查看详情')),
      ]),
      onClose: () => {
        this.showFilterTips = true;
      },
    });
  }
  /**
   * 显示过滤IP详情
   */
  public handleShowDetail() {
    this.showFilterDialog = true;
  }
}
