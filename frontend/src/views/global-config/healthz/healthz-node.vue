<template>
  <div class="monitoring-node-box">
    <bk-popover
      theme="light"
      placement="bottom-start"
      :ref="`node-${category}`"
      :disabled="!filteredNodeData.length"
      :tippy-options="{ boundary: 'window' }">
      <div :class="`monitoring-node ${nodeTheme}`">
        <span class="text-ellipsis" v-bk-overflow-tips>{{ nodeName }}</span>
      </div>
      <ul :class="['tips-list', { 'is-abnormal': nodeTheme === 'error' }]" slot="content">
        <li
          v-for="(tip, index) in filteredNodeData"
          :key="index"
          :class="`list-item ${tip.theme}`"
          @click="showPopupDialog(tip)">
          <span v-if="tip.theme !== 'running'" :class="`tips-status-icon ${tip.theme}`">
            <i class="nodeman-icon nc-remind-fill"></i>
          </span>
          <span class="list-item-text text-ellipsis" v-bk-overflow-tips>
            {{tip.server_ip}} {{tip.description}} {{tip.value}}
          </span>
        </li>
      </ul>
    </bk-popover>
    <div :class="`monitoring-node-tail ${tailBorder}`"></div>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';
import { ConfigStore } from '@/store/index';

@Component({ name: 'HealthzNode' })
export default class HealthzNode extends Vue {
  @Prop({ type: String, default: 'backend' }) private readonly category!: string;
  @Prop({ type: String, default: '' }) private readonly nodeName!: string;
  @Prop({ type: Boolean, default: false }) private readonly showLine!: boolean;

  private get selectedIPs() {
    return ConfigStore.selectedIPs;
  }
  private get nodeData() {
    const data: any[] = [];
    ConfigStore.healthzData.forEach((item) => {
      if (this.nodeName === item.node_name) {
        const { value, message, status = -1 } = item.result || {};
        data.push({
          ...item,
          server_ip: item.server_ip,
          description: item.description,
          name: item.node_name,
          theme: this.statusTransformToTheme(status),
          api_list: Object.prototype.hasOwnProperty.call(item.result, 'api_list') ? item.result.api_list : [],
          value,
          message,
          status,
        });
      }
    });
    return data;
  }

  // 根据前端显示的选中的ip列表过滤本地数据
  private get filteredNodeData() {
    // 如果当前组件为saas依赖周边，则直接返回数据
    if (ConfigStore.saasDependenciesComponent.indexOf(this.nodeName) > -1) return this.nodeData;
    const resultData: any[] = [];
    this.nodeData.forEach((item) => {
      if (this.selectedIPs.indexOf(item.server_ip) > -1) {
        resultData.push(item);
      }
    });
    resultData.sort((a, b) => b.status - a.status);
    return resultData;
  }
  // 当前节点所有数据的状态列表
  private get statusList() {
    const statusList: number[] = [];
    this.filteredNodeData.forEach((item) => {
      if (this.nodeName === item.name) {
        statusList.push(item.status);
      }
    });
    return statusList;
  }
  // 由当前数据状态列表计算而来的颜色
  private get nodeTheme() {
    if (this.category === 'saas') {
      return 'running';
    }
    if (!this.statusList.length) {
      return '';
    }
    const max = Math.max(...this.statusList);
    return max > 1 ? 'error' : this.statusTransformToTheme(max);
  }
  private get tailBorder() {
    if (this.showLine) {
      return this.nodeTheme === 'running' ? 'solid' : 'dashed';
    }
    return '';
  }

  @Emit('show-dialog')
  public showPopupDialog(tip: any) {
    const ref: any = this.$refs[`node-${this.category}`];
    ref?.hideHandler();
    return {
      nodeName: this.nodeName,
      category: this.category,
      tip,
    };
  }

  public statusTransformToTheme(status?: number) {
    if (status === 0) {
      return 'running';
    }
    if (status === 1) {
      return 'warning';
    }
    if (status === 2) {
      return 'error';
    }
    return '';
  }
}
</script>

<style lang="postcss" scoped>
  .monitoring-node-box {
    display: inline-flex;
    height: 40px;
    .monitoring-node {
      display: flex;
      align-items: center;
      padding: 0 10px;
      width: 140px;
      height: 40px;
      line-height: 40px;
      border-left: 2px solid;
      border-color: #979ba5;
      border-radius: 1px;
      font-size: 12px;
      color: #63656e;
      background: #f5f6fa;
      &:hover {
        padding-left: 8px;
        padding-right: 9px;
        border: 1px solid;
        border-left: 4px solid;
      }
      &.error {
        border-color: #ea3636;
      }
      &.running {
        border-color: #08cba4;
      }
    }
    .monitoring-node-tail {
      position: relative;
      width: 40px;
      &::before {
        position: absolute;
        display: block;
        content: "";
        top: 20px;
        left: 0;
        width: 100%;
      }
      &.solid::before {
        border-bottom: 1px solid #c4c6cc;
      }
      &.dashed::before {
        border-bottom: 1px dashed #c4c6cc;
      }
    }
  }
  .tips-list {
    padding: 9px 0;
    width: 280px;
    max-height: 220px;
    overflow: auto;
    &.is-abnormal .list-item {
      padding-left: 24px;
    }
    .list-item {
      position: relative;
      display: flex;
      align-items: center;
      padding: 0 4px;
      width: 100%;
      line-height: 22px;
      font-size: 12px;
      color: #63656e;
      &:hover {
        background: #f4f4f4;
        cursor: pointer;
      }
      .tips-status-icon {
        position: absolute;
        left: 4px;
        width: 20px;
        font-size: 12px;
      }
    }
    .list-item-text {
      flex: 1;
    }
    .error {
      color: #ea3636;
    }
    .warning {
      color: #ff9c01;
    }
  }
</style>
