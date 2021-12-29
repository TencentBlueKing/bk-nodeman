<template>
  <bk-collapse v-model="activeName" v-bkloading="{ isLoading }">
    <bk-collapse-item
      v-for="(item, index) in list"
      :key="item.name"
      :name="item.name"
      hide-arrow
      :class="{ 'is-first': index === 0 }">
      <div class="collapse-title">
        <div class="left">
          <i :class="[
            'bk-icon icon-down-shape arrow',
            { active: activeName.includes(item.name) }
          ]">
          </i>
          <i18n :path="item.path" class="title ml10">
            <span class="num">{{ pagination.count }}</span>
          </i18n>
        </div>
        <span class="more-btn" v-if="item.name === 'host'" @click.stop="handleShowOperate($event)">
          <i class="bk-icon icon-more"></i>
        </span>
      </div>
      <template #content>
        <component
          :is="comMap[item.com]"
          v-bind="{
            selection: false,
            operate: false,
            pagination: pagination
          }"
          :data="tableData"
          @paginationChange="handlePaginationChange">
        </component>
      </template>
    </bk-collapse-item>
  </bk-collapse>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import StaticContentTable from './static-content-table.vue';
import NodePreviewTable from './node-preview-table.vue';
import MoreOperate from '@/views/plugin/plugin-rule/components/more-operate.vue';
import { VueConstructor } from 'vue';
import { copyText } from '@/common/util';
import { IPagination } from '@/types';

interface ICollapseItem {
  name: string
  com: VueConstructor
  path: string
  total?: number
  data?: any[]
}

@Component({ name: 'node-preview' })
export default class NodePreview extends Vue {
  @Prop({ type: String, default: 'TOPO' }) private readonly active!: 'TOPO' | 'HOST';
  @Prop({ type: Function }) private readonly getTableList!: Function;
  @Prop({ type: Array, default: () => [] }) private readonly collapseList!: Dictionary[];
  private comMap = {
    staticContentTable: StaticContentTable,
    nodePreviewTable: NodePreviewTable,
  };
  private isLoading = false;
  private tableData: any[] = [];
  private activeName: string[] = ['host', 'node'];
  private instance: MoreOperate = new MoreOperate().$mount();
  private popoverInstance: any = null;
  private pagination: IPagination = {
    current: 1,
    count: 0,
    limit: 10,
    limitList: [10, 20, 50, 100],
  };

  private get list() {
    if (this.collapseList.length) {
      return [...this.collapseList];
    }
    return this.active === 'TOPO' ? [
      { name: 'node', com: 'nodePreviewTable', path: '已选节点' },
    ] : [
      { name: 'host', com: 'staticContentTable', path: '已选主机' },
    ];
  }

  private created() {
    this.instance.data = [
      {
        id: 'copyAllIp',
        name: this.$t('复制全部IP'),
      },
      {
        id: 'copyNormalIp',
        name: this.$t('复制正常IP'),
      },
      {
        id: 'copyAbnormalIp',
        name: this.$t('复制异常IP'),
      },
    ];
    this.instance.$on('click', this.handleMenuClick);
    this.handlePaginationChange();
  }

  private beforeDestroy() {
    this.instance.$off('click', this.handleMenuClick);
    this.instance.$destroy();
    this.popoverInstance && (this.popoverInstance = null);
  }

  private handleMenuClick(menu: any) {
    if (menu.disabled) return;
    this.copyIP(menu.id);
    this.destroyPopover();
  }

  private async resetTableData({ page, pagesize, conditions }: {
    page?: number
    pagesize?: number
    conditions?: any
  }) {
    const formatParams: { [key: string]: any } = {
      page: page || this.pagination.current,
      pagesize: pagesize || this.pagination.limit,
    };
    if (conditions) {
      formatParams.conditions = conditions;
    }
    return this.getTableList(formatParams);
  }
  private async handlePaginationChange(params?: { page: number, pagesize: number }) {
    this.isLoading = true;
    if (params) {
      this.pagination.current = params.page;
      this.pagination.limit = params.pagesize;
    }
    const { current, limit } = this.pagination;
    const { total, list } = await this.resetTableData({
      page: current,
      pagesize: limit,
    });
    this.tableData = list;
    this.pagination.count = total;
    this.isLoading = false;
  }
  public handleShowOperate(e: Event) {
    this.popoverInstance = this.$bkPopover(e.target as EventTarget, {
      content: this.instance.$el,
      trigger: 'manual',
      arrow: false,
      theme: 'light menu',
      maxWidth: 280,
      offset: '0, 5',
      sticky: true,
      duration: [275, 0],
      interactive: true,
      boundary: 'window',
      placement: 'bottom',
      onHidden: () => {
        this.popoverInstance && this.popoverInstance.destroy();
        this.popoverInstance = null;
      },
    });
    this.popoverInstance.show();
  }
  private async copyIP(type: string) {
    let data = [];
    const params: { [key: string]: any } = {
      page: 1,
      pagesize: -1,
    };
    if (type === 'copyNormalIp') {
      params.conditions = [{
        key: 'status',
        value: ['RUNNING'],
      }];
    } else if (type === 'copyAbnormalIp') {
      params.conditions = [{
        key: 'status',
        value: ['TERMINATED'],
      }];
    }
    const { list, total } = await this.resetTableData(params);
    data = list;
    copyText(data.map((item: any) => item.inner_ip).join(), () => {
      this.$bkMessage({ message: this.$t('IP复制成功', { num: total }), theme: 'success' });
    });
  }
  private destroyPopover() {
    this.popoverInstance && this.popoverInstance.destroy();
    this.popoverInstance = null;
  }
}
</script>
<style lang="postcss" scoped>
>>> .bk-collapse-item {
  &-header {
    background: #fafbfd;
    border: 1px solid #dcdee5;
    border-top: 0;
    .bk-icon {
      font-size: 14px;
      position: relative;
      top: -1px;
    }
  }
  &-content {
    padding: 0;
    border-left: 1px solid #dcdee5;
    border-right: 1px solid #dcdee5;
  }
}
>>> .bk-table {
  .is-first .cell {
    padding-left: 50px;
  }
  th {
    background-color: #fff;
  }
  &-empty-block {
    border-bottom: 1px solid #dcdee5;
  }
}
.is-first {
  >>> .bk-collapse-item-header {
    border-top: 1px solid #dcdee5;
  }
}
.collapse-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 0 10px;
  height: 42px;
  .left {
    height: 42px;
  }
  .arrow {
    transition: transform .2s ease-in-out;
    transform: rotate(-90deg);
    color: #63656e;
    display: inline-block;
    &.active {
      transform: rotate(0deg);
    }
  }
  .title {
    color: #63656e;
    font-size: 12px;
    font-weight: 700;
    .num {
      color: #3a84ff;
    }
  }
  .more-btn {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: #979ba5;
    i {
      font-size: 22px;
    }
    &:hover {
      color: #3a84ff;
      background: #dcdee5;
    }
  }
}
</style>
