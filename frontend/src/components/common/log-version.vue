<template>
  <bk-dialog
    width="1105"
    v-model="show"
    :show-footer="false"
    @value-change="handleValueChange">
    <div class="log-version" v-bkloading="{ isLoading: loading }">
      <div class="log-version-left">
        <ul class="left-list">
          <li
            v-for="(item,index) in logList"
            :class="['left-list-item', { 'item-active': index === active }]"
            :key="index"
            @click="handleItemClick(index)">
            <span class="item-title">{{item.title}}</span>
            <span class="item-date">{{item.date}}</span>
            <span v-if="index === current" class="item-current"> {{ $t('当前版本') }} </span>
          </li>
        </ul>
      </div>
      <div class="log-version-right">
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="detail-container" v-html="currentLog.detail"></div>
      </div>
    </div>
  </bk-dialog>
</template>
<script lang="ts">
import { Vue, Component, Emit, Watch, Model } from 'vue-property-decorator';
import { axiosInstance } from '@/api';

interface ILog {
  title: string
  date: string
  detail: string
}

@Component({ name: 'log-version' })
export default class LogVersion extends Vue {
  @Model('change', { default: false, type: Boolean }) private readonly dialogShow!: boolean;

  private show = false;
  private loading = false;
  private current = 0;
  private active = 0;
  private logList: ILog[] = [];

  private get currentLog() {
    return this.logList[this.active] || {};
  }

  @Watch('dialogShow')
  private async handleShowChange(v: boolean) {
    this.show = v;
    if (v) {
      this.loading = true;
      this.logList = await this.getVersionLogsList();
      if (this.logList.length) {
        await this.handleItemClick();
      }
      this.loading = false;
    }
  }

  @Emit('update-dialogShow')
  private beforeDestroy() {
    this.show = false;
    return false;
  }

  //  dialog显示变更触发
  @Emit('change')
  private handleValueChange(isShow: boolean) {
    return isShow;
  }
  //  点击左侧log查看详情
  private async handleItemClick(v = 0) {
    this.active = v;
    if (!this.currentLog.detail) {
      this.loading = true;
      const detail = await this.getVersionLogsDetail();
      const currentLog = this.logList[v];
      currentLog.detail = detail;
      this.loading = false;
    }
  }
  //  获取左侧版本日志列表
  private async getVersionLogsList() {
    const url = 'version_log/version_logs_list/';
    const { data } = await axiosInstance({
      method: 'get',
      url,
      baseURL: window.PROJECT_CONFIG.SITE_URL,
    }).catch(() => ({ data: [] }));
    return data.map((item: string[]) => ({ title: item[0], date: item[1], detail: '' }));
  }
  // 获取右侧对应的版本详情
  private async getVersionLogsDetail() {
    const url = 'version_log/version_log_detail/';
    const { data } = await axiosInstance({
      method: 'get',
      url,
      baseURL: window.PROJECT_CONFIG.SITE_URL,
      params: {
        log_version: this.currentLog.title,
      },
    }).catch(() => ({ data: '' }));
    return data;
  }
}
</script>
<style lang="scss" scoped>
.log-version {
  display: flex;
  margin: -33px -24px -26px;
  &-left {
    flex: 0 0 260px;
    background-color: #fafbfd;
    border-right: 1px solid #dcdee5;
    padding: 40px 0;
    display: flex;
    font-size: 12px;
    .left-list {
      border-top: 1px solid #dcdee5;
      border-bottom: 1px solid #dcdee5;
      height: 520px;
      overflow: auto;
      display: flex;
      flex-direction: column;
      width: 100%;
      &-item {
        flex: 0 0 54px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding-left: 30px;
        position: relative;
        border-bottom: 1px solid #dcdee5;
        &:hover {
          cursor: pointer;
          background-color: #fff;
        }
        .item-title {
          color: #313238;
          font-size: 16px;
        }
        .item-date {
          color: #979ba5;
        }
        .item-current {
          position: absolute;
          right: 20px;
          top: 8px;
          background-color: #699df4;
          border-radius: 2px;
          width: 58px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
        }
        &.item-active {
          background-color: #fff;
          &::before {
            content: " ";
            position: absolute;
            top: 0px;
            bottom: 0px;
            left: 0;
            width: 6px;
            background-color: #3a84ff;
          }
        }
      }
    }
  }
  &-right {
    flex: 1;
    padding: 25px 30px 50px 45px;
    .detail-container {
      max-height: 525px;
      overflow: auto;
    }
  }
}
</style>
