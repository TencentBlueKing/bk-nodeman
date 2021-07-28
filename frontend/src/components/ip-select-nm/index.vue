<template>
  <div class="ip-select">
    <slot name="tab">
      <Tab :list="tabList" v-model="activeTab" class="mb20"></Tab>
    </slot>
    <slot name="content">
      <component
        :is="currentTab.com"
        class="ip-select-content"
        v-bind="propData">
      </component>
    </slot>
    <slot name="footer">
      <SelectFooter :footer-button="footerButton" @confirm="handleConfirm" @cancel="handleCancel">
        <template #default>
          <i18n path="已选择" tag="div" class="node-count" @click="handleShowPreview">
            <span class="num">1</span>
            <span class="num">2</span>
          </i18n>
        </template>
      </SelectFooter>
    </slot>
    <bk-dialog width="60%" :position="{ top: 100 }" v-model="showPreview" :draggable="false">
      <template #header>
        <div class="node-preview">
          <span class="title">{{ $t('已选项预览') }}</span>
          <i18n path="已选择" class="count">
            <span class="num">8</span>
            <span class="num">3</span>
          </i18n>
        </div>
      </template>
      <NodePreview :list="previewList"></NodePreview>
    </bk-dialog>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';
import Tab from './ip-select-tab.vue';
import StaticContent from './static-content.vue';
import DynamicContent from './dynamic-content.vue';
import SelectFooter from './ip-select-footer.vue';
import NodePreview from './node-preview.vue';
import { VueConstructor } from 'vue';

interface ITabPanel {
  name: string
  label: string
  visible?: boolean
  disabled?: boolean
  com: VueConstructor
}

@Component({
  name: 'ip-select',
  components: {
    Tab,
    SelectFooter,
    DynamicContent,
    NodePreview,
  },
})
export default class IpSelect extends Vue {
  @Prop({
    default: () => [
      {
        name: 'static-topo',
        label: window.i18n.t('静态 - IP 选择'),
        com: StaticContent,
      },
      {
        name: 'dynamic-topo',
        label: window.i18n.t('动态 - 拓扑选择'),
        com: DynamicContent,
      },
    ],
  })
  private readonly tabList!: ITabPanel[];
  @Prop({ default: 'static-topo' }) private readonly active!: string;
  @Prop({ default: true }) private readonly footerButton!: boolean;
  @Prop({ default: () => ({}), type: Object }) private readonly propData!: Dictionary;

  private activeTab = this.active;
  private showPreview = false;
  private previewList = [
    {
      name: 'host',
      com: 'staticContentTable',
      path: '已选主机',
      data: [
        {
          inner_ip: '66.66.88.88',
          status: 'TERMINATED',
          status_display: '异常',
          bk_cloud_name: `直连区域${Math.random() * 10}`,
          bk_host_name: 'centos',
          os_type: 'linux',
          disabled: true,
          disabled_msg: 'xxxxxxx',
        },
        {
          inner_ip: '66.66.88.88',
          status: 'RUNNING',
          status_display: '正常',
          bk_cloud_name: '直连区域',
          bk_host_name: 'centos2',
          os_type: 'windows',
        },
      ],
    },
    {
      name: 'node',
      com: 'nodePreviewTable',
      path: '已选节点',
      data: [],
    },
  ];

  private get currentTab() {
    const tab = this.tabList.find(item => item.name === this.activeTab);
    return tab ? tab : {};
  }

  public handleShowPreview() {
    this.showPreview = true;
  }

  @Emit('confirm')
  public handleConfirm() {}
  @Emit('cancel')
  public handleCancel() {}
}
</script>
<style lang="postcss" scoped>
>>> .bk-dialog {
  width: 60%;
  &-body {
    padding: 0;
    height: 550px;
  }
}
.ip-select {
  border: 1px solid #dcdee5;
  height: 100%;
  display: flex;
  flex-direction: column;
  &-content {
    flex: 1;
  }
}
.node-count {
  height: 32px;
  line-height: 32px;
  padding: 0 13px;
  cursor: pointer;
  &:hover {
    background: #f0f1f5;
    border-radius: 2px;
  }
  .num {
    color: #3a84ff;
  }
}
.node-preview {
  text-align: left;
  .title {
    font-size: 20px;
    color: #000;
  }
  .count {
    margin-left: 10px;
    font-size: 14px;
  }
  .num {
    color: #3a84ff;
  }
}
</style>
