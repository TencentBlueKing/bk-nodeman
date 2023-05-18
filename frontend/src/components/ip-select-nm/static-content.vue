<template>
  <div class="content">
    <section class="content-left">
      <slot name="left">
        <div class="left-input">
          <bk-input
            :placeholder="$t('搜索拓扑节点')"
            right-icon="bk-icon icon-search"
            class="mb20">
          </bk-input>
        </div>
        <StaticTopo class="left-topo" @select-change="handleSelectChange"></StaticTopo>
      </slot>
    </section>
    <section class="content-right">
      <slot name="right">
        <div class="mb20 content-right-filter">
          <div class="bk-button-group mr10" v-if="showStatus">
            <bk-button
              v-for="item in btnTab.list"
              :key="item.id"
              :class="btnTab.active === item.id ? 'is-selected' : ''"
              @click="handleTabChange(item)">
              {{ item.name }}
            </bk-button>
          </div>
          <bk-input
            :placeholder="$t('输入主机IP/主机名/操作系统/管控区域进行搜索...')"
            right-icon="bk-icon icon-search">
          </bk-input>
        </div>
        <StaticContentTable :data="tableData" :show-status="showStatus"></StaticContentTable>
        <Pagination class="mt15" v-if="tableData.length"></Pagination>
      </slot>
    </section>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Watch, Prop } from 'vue-property-decorator';
import StaticContentTable from './static-content-table.vue';
import StaticTopo from './static-topo.vue';
import Pagination from './table-pagination.vue';
import { TranslateResult } from 'vue-i18n';

interface IOption {
  id: string | number
  name: string | TranslateResult
}
interface ITab {
  active: string | number
  list: IOption[]
}

@Component({
  name: 'static-content',
  components: {
    StaticContentTable,
    StaticTopo,
    Pagination,
  },
})
export default class StaticContent extends Vue {
  @Prop({ default: false }) private readonly showStatus!: boolean;
  private selectNodeId: number | string = '';
  private tableData: any[] = [];
  private btnTab: ITab= {
    active: '',
    list: [],
  };

  @Watch('selectNodeId')
  public handleSelectNodeChange() {
    this.handleGetTableData();
  }

  private created() {
    this.btnTab.list = [
      {
        id: 'deploy',
        name: this.$t('已部署'),
      },
      {
        id: 'all_host',
        name: this.$t('全部主机'),
      },
    ];
  }

  public handleSelectChange(treeNode: any) {
    this.selectNodeId = treeNode.id;
  }

  public handleGetTableData() {
    this.tableData = [
      {
        inner_ip: '66.66.88.88',
        status: 'TERMINATED',
        status_display: '异常',
        bk_cloud_name: `直连区域${Math.random() * 10}`,
        bk_host_name: 'centos',
        os_type: 'linux',
        disabled: true,
        disabled_msg: 'xxxxxxx',
        selection: false,
        id: 1,
      },
      {
        inner_ip: '66.66.88.88',
        status: 'RUNNING',
        status_display: '正常',
        bk_cloud_name: '直连区域',
        bk_host_name: 'centos2',
        os_type: 'windows',
        selection: false,
        id: 2,
      },
      {
        inner_ip: '66.66.88.88',
        status: 'TERMINATED',
        status_display: '异常',
        bk_cloud_name: `直连区域${Math.random() * 10}`,
        bk_host_name: 'centos',
        os_type: 'linux',
        disabled: false,
        disabled_msg: 'xxxxxxx',
        selection: true,
        id: 3,
      },
      {
        inner_ip: '66.66.88.88',
        status: 'TERMINATED',
        status_display: '异常',
        bk_cloud_name: `直连区域${Math.random() * 10}`,
        bk_host_name: 'centos',
        os_type: 'linux',
        disabled: false,
        disabled_msg: 'xxxxxxx',
        selection: true,
        id: 4,
      },
    ];
  }
  public handleTabChange(item: IOption) {
    this.btnTab.active = item.id;
  }
}
</script>
<style lang="postcss" scoped>
>>> .bk-big-tree {
  .bk-big-tree-node:not(.has-link-line) {
    .node-options {
      padding-left: 24px;
    }
    .node-content .node-label {
      padding-right: 24px;
      .num.selected {
        background: #a3c5fd;
        color: #fff;
      }
    }
  }
}
.content {
  &-left {
    height: 100%;
    float: left;
    width: 370px;
    border-right: 1px solid #e7e8ed;
    .left-input {
      padding: 0 24px;
    }
  }
  &-right {
    margin-left: 370px;
    padding: 0 24px 16px 24px;
    &-filter {
      display: flex;
      >>> .bk-form-control {
        flex: 1;
      }
    }
  }
}
</style>
