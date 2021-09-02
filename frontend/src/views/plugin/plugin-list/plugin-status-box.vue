<template>
  <div class="col-status">
    <loading-icon class="mr5" v-if="status === 'running'"></loading-icon>
    <span :class="`status-mark status-${status}`" v-else></span>
    <slot>
      <span v-if="showText">{{ statusMap[status] | filterEmpty }}</span>
    </slot>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

type IStatus = 'pending' | 'running' | 'success' | 'failed';

@Component({ name: 'plugin-status-box' })
export default class PluginStatusBox extends Vue {
  @Prop({ type: String, default: '' }) private readonly status!: IStatus;
  @Prop({ type: Boolean, default: true }) private readonly showText!: boolean;

  private statusMap: Dictionary = {
    pending: this.$t('队列中'), // 队列中
    running: this.$t('部署中'), // 部署中
    success: this.$t('成功'), // 成功
    failed: this.$t('失败'),   // 失败
  };
}
</script>
<style lang="postcss" scoped>
.task-list {
  padding: 3px 2px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
}
.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.task-item + .task-item {
  margin-top: 10px;
}
.task-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
}
.task-status {
  margin-left: 20px;
  width: 60px;
}
.status-success {
  border-color: #e5f6ea;
  background: #3fc06d;
}
.status-failed {
  border-color: #ffe6e6;
  background: #ea3636;
}
</style>
