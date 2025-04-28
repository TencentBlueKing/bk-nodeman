<template>
  <section>
    <section class="nodeman-nav-wrapper">
      <div class="page-header">
        <span class="content-icon" @click="handleBack">
          <i class="nodeman-icon nc-back-left"></i>
        </span>
        <span class="content-header">{{ `${ $t('任务详情') } ${ $filters('filterEmpty', detail.jobTypeDisplay) }` }}</span>
        <div class="content-subtitle">
          <span v-if="manualWaiting" class="tab-badge bg-filtered">{{ manualWaitingTitle }}</span>
          <span v-else :class="`tab-badge bg-${taskStatus}`">{{ titleStatusMap[taskStatus] || $t('状态未知') }}</span>
        </div>
      </div>
      <div class="task-detail-container mt20">
        <ul :class="['detail-info-list', { 'is-plugin': detail.stepType === 'PLUGIN', en: isEnLanguage }]">
          <li class="detail-info-item" v-for="(item, index) in taskInfoList" :key="index">
            <span class="info-label" v-if="item.name">
              {{ item.name }}
            </span>
            <span class="info-value text-ellipsis" v-if="item.name" v-bk-overflow-tips>
              <template v-if="item.id === 'createdBy' && ENABLE_MULTI_TENANT_MODE && detail[item.id]">
                <bk-user-display-name :user-id="detail[item.id]"></bk-user-display-name>
              </template>
              <template v-else>
                {{ detail[item.id] | filterEmpty }}
              </template>
            </span>
          </li>
        </ul>
      </div>
    </section>
  </section>
</template>

<script lang="ts">
import { Component, Prop, Mixins } from 'vue-property-decorator';
import Tips from '@/components/common/tips.vue';
import RouterBackMixin from '@/common/router-back-mixin';
import { MainStore } from '@/store';
import BkUserDisplayName from '@blueking/bk-user-display-name';

@Component({
  name: 'task-detail-info',
  components: {
    Tips,
  },
})
export default class TaskDeatail extends Mixins(RouterBackMixin) {
  @Prop({ type: String, default: '', required: true }) private readonly taskStatus!: string;
  @Prop({ type: Object, default: () => ({}) }) private readonly detail!: Dictionary;
  @Prop({ type: String, default: 'agent' }) private readonly operateHost!: 'Agent' | 'Proxy' | 'Plugin';
  @Prop({ type: Boolean, default: false }) private readonly manualWaiting!: boolean;

  private titleStatusMap = {
    running: window.i18n.t('正在执行'),
    failed: window.i18n.t('执行失败'),
    part_failed: window.i18n.t('部分失败'),
    success: window.i18n.t('执行成功'),
    stop: window.i18n.t('已终止'),
    pending: window.i18n.t('等待执行'),
    terminated: window.i18n.t('已终止'),
    filtered: window.i18n.t('已忽略'),
  };
  private taskInfoList = [
    { name: window.i18n.t('任务ID'), id: 'jobId' },
    { name: window.i18n.t('开始时间'), id: 'timestamp' },
    { name: window.i18n.t('总耗时'), id: 'costTime' },
    { name: window.i18n.t('任务类型'), id: 'stepTypeDisplay' },
    { name: window.i18n.t('操作类型'), id: 'opTypeDisplay' },
    { name: window.i18n.t('执行账号'), id: 'createdBy' },
  ];

  private get isEnLanguage() {
    return MainStore.language === 'en';
  }
  private get manualWaitingTitle() {
    return /UN/ig.test(this.detail.jobType) ? this.$t('等待手动卸载') : this.$t('等待手动安装');
  }
  
  private get API_BASE_URL() {
    return window.PROJECT_CONFIG.API_BASE_URL;
  }
  private get ENABLE_MULTI_TENANT_MODE() {
    return window.PROJECT_CONFIG.ENABLE_MULTI_TENANT_MODE;
  }
  
  private created() {
    if (this.API_BASE_URL) {
      BkUserDisplayName.configure({
        // 必填，租户 ID
        tenantId: window.PROJECT_CONFIG.TENANT_ID,
        // 必填，网关地址
        apiBaseUrl: window.PROJECT_CONFIG.API_BASE_URL,
        // 可选，缓存时间，单位为毫秒, 默认 5 分钟, 只对单一值生效
        cacheDuration: 1000 * 60 * 5,
        // 可选，当输入为空时，显示的文本，默认为 '--'
        emptyText: '--'
      });
    }
    if (this.operateHost === 'Plugin') {
      let name = this.$t('插件名称');
      let id = 'pluginName';
      if (this.detail.category === 'policy') {
        name = this.$t('策略名称');
        id = 'name';
      }
      this.taskInfoList.splice(1, 0, { name, id });
      this.taskInfoList.push({ name: '', id: '' });
    }
  }

  public handleBack() {
    const parentRouterName = MainStore.routerBackName;
    if (parentRouterName === 'taskList') {
      MainStore.updateRouterBackName();
      this.$router.replace({ name: parentRouterName });
    } else {
      this.routerBack();
    }
  }
}
</script>

<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";
  @import "@/css/variable.css";

  >>> .icon-down-wrapper {
    position: relative;
    left: 3px;
  }
  .page-header .tab-badge {
    padding: 0 4px;
    line-height: 16px;
    border-radius: 2px;
    font-weight: 600;
    color: #fff;
  }
  .nodeman-nav-wrapper {
    padding: 20px 24px 15px 24px;
    background: #f5f7fa;
  }
  .manual-tips-wrapper {
    padding: 0 60px;
  }
  .task-detail-container {
    display: flex;
    justify-content: space-between;
  }
  .detail-info-list {
    display: flex;
    flex-wrap: wrap;
    min-width: 690px;
    max-width: 879px; /* 比四倍少1 */
    &.is-plugin {
      max-width: 920px; /* 四倍 */
    }
    &.en {
      min-width: 840px;
      max-width: 1079px;
      &.is-plugin {
        max-width: 1120px;
      }
      .detail-info-item {
        min-width: 270px;
      }
      .info-label {
        width: 90px;
      }
    }
  }
  .detail-info-item {
    margin-right: 10px;
    margin-bottom: 10px;
    display: flex;
    flex: 1;
    min-width: 220px;
    line-height: 16px;
    font-size: 12px;
    .info-label {
      position: relative;
      display: inline-block;
      width: 50px;

      /* width: 80px; */
      color: #b2b5bd;
      &::after {
        content: ":";
        position: absolute;
        right: -5px;
      }
    }
    .info-value {
      display: inline-block;
      flex: 1;
      margin-left: 10px;
      color: $defaultFontColor;
    }
  }
</style>
