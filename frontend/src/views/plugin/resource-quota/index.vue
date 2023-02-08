<template>
  <article class="resource-quota" v-bkloading="{ isLoading: loading }">
    <section class="page-head">
      <span class="title">{{ $t('资源配额') }}</span>
    </section>

    <div class="page-container">
      <div class="page-tips-wrapper">
        <tips :list="[$t('资源配额tip'), $t('资源配额规则tip'), $t('资源配额场景tip')]" />
      </div>

      <section class="page-body" v-if="hasPageAuth">
        <section class="side-block pb20">
          <div class="side-search">
            <bk-input
              :placeholder="$t('请输入关键词')"
              :right-icon="'bk-icon icon-search'"
              v-model="searchKey"
              @change="handleSearchChange">
            </bk-input>
          </div>
          <!-- <ResourceTree
            class="resource-tree"
            ref="treeRef"
            :tree-data="treeData"
            :selected-node="curNode"
            :load-method="loadTreeChild"
            :node-fold-able="(item) => item.bk_obj_id === 'biz'"
            :node-load-able="(item) => item.bk_obj_id === 'biz'"
            @selected="handleTreeSelected">
          </ResourceTree> -->
          <ResourceTreeItem
            :node-list="nodeList"
            @click="handleClickNode">
          </ResourceTreeItem>
        </section>
        <section class="content-body" v-bkloading="{ isLoading: pluginLoading }">
          <template v-if="curNode && curNode.id">
            <template v-if="curNode.type === 'template'">
              <div class="content-body-head mb20">
                <p class="content-body-title">{{ moduleName }}</p>
                <bk-button theme="primary" :disabled="moduleId < 0" @click="editResourceQuota">
                  {{ $t('编辑') }}
                </bk-button>
              </div>
              <section class="content-body-table">
                <bk-table :data="pluginList" :max-height="windowHeight - 192">
                  <bk-table-column :label="$t('插件名称')" prop="plugin_name" :resizable="false"></bk-table-column>
                  <bk-table-column :label="$t('总数运行中异常')" :resizable="false">
                    <template #default="{ row }">
                      <div>
                        <span class="num">{{ row.total }}</span>
                        <span>/</span>
                        <span class="num running">{{ row.running }}</span>
                        <span>/</span>
                        <span class="num abort">{{ row.terminated }}</span>
                      </div>
                    </template>
                  </bk-table-column>
                  <bk-table-column
                    label="CPU配额及单位"
                    prop="cpu"
                    align="right"
                    :resizable="false"
                    :render-header="tipsHeadRender" />
                  <bk-table-column
                    label="内存配额及单位"
                    prop="mem"
                    align="right"
                    :resizable="false"
                    :render-header="tipsHeadRender" />
                  <bk-table-column width="40"></bk-table-column>
                </bk-table>
              </section>
            </template>
            <EmptyServiceBox v-else @click-link="handleEmptyLink" />
          </template>
        </section>
      </section>
      <exception-page
        v-else
        class="resource-quota-page"
        type="notPower"
        :title="$t('无业务权限')"
        :btn-text="$t('申请权限')"
        :has-border="false"
        @click="handleApplyPermission">
      </exception-page>
    </div>
  </article>
</template>
<script lang="ts">
import { Component, Watch, Mixins, Prop, Ref } from 'vue-property-decorator';
import { MainStore, PluginStore } from '@/store/index';
import ResourceTreeItem from './resource-tree-item.vue';
import HeaderFilterMixins from '@/components/common/header-filter-mixins';
import { IBkBiz, IBkColumn } from '@/types';
import { CreateElement } from 'vue';
import TableHeader from '@/components/setup-table/table-header.vue';
import { debounce } from '@/common/util';
import ExceptionPage from '@/components/exception/exception-page.vue';
import ExceptionCard from '@/components/exception/exception-card.vue';
import EmptyServiceBox from '@/components/exception/EmptyServiceBox.vue';
import Tips from '@/components/common/tips.vue';
import { bus } from '@/common/bus';
import { Route } from 'vue-router';
import { appendChild, getFormatTree, setActiveNode, IData, ITreeNode } from './tree-fn';

Component.registerHooks([
  'beforeRouteLeave',
]);

@Component({
  name: 'resourceQuota',
  components: {
    ResourceTreeItem,
    TableHeader,
    ExceptionPage,
    ExceptionCard,
    EmptyServiceBox,
    Tips,
  },
})
export default class ResourceQuota extends Mixins(HeaderFilterMixins) {
  @Prop({ type: Number, default: null }) private readonly bizId!: number;
  @Prop({ type: Number, default: null }) private readonly moduleId!: number;
  @Ref('treeRef') private readonly treeRef!: any;

  public needFix = false;
  public loading = true;
  public pluginLoading = false;
  public action = 'plugin_view';
  public treeSourceList: ITreeNode[] = [];
  public treeSourceMap: { [key: number]: ITreeNode } = {};
  public nodeList: ITreeNode[] = [];
  public curNode: ITreeNode | Dictionary = {};
  public searchKey = '';
  public treeData: any[] = [];
  public pluginListMap: any = {};
  public pluginList: any[] = [];
  public headTipsMap = {
    cpu: 'CPU配额tip',
    mem: '内存配额tip',
  };
  // public biz: number[] = [];
  public handleSearchChange!: Function;

  private get moduleName() {
    return this.curNode?.name || '';
  }
  private get windowHeight() {
    return MainStore.windowHeight;
  }
  private get selectedBiz() {
    return MainStore.selectedBiz;
  }
  private get bkBizList() {
    return MainStore.bkBizList.filter(item => !item.disabled);
  }
  private get hasPageAuth() {
    return !!this.bkBizList.length;
  }

  @Watch('$route')
  public handleBeforeReset() {
    if (this.needFix) {
      this.fixRouteInfo();
    } else {
      this.updateTreeStatus();
      this.loading = false;
    }
  }

  @Watch('selectedBiz')
  public async handleBizChange(newVal: number[], oldVal: number[]) {
    if (this.needFix) {
      this.fixRouteInfo();
    } else {
      const sortVal = [...newVal].sort((a, b) => a - b);
      if (sortVal.length && !sortVal.includes(this.bizId)) {
        this.needFix = true;
        const bizId = sortVal.length ?  sortVal[0] : this.bkBizList[0]?.bk_biz_id;
        const moduleId = this.diffRouteModuleId(bizId);
        this.$router.replace({ query: { bizId: `${bizId}`, moduleId: `${moduleId}` } });
      } else if (oldVal.length !== sortVal.length) {
        this.updateTreeStatus();
      }
    }
  }

  private async created() {
    this.handleSearchChange = debounce(300, this.handleSearchTree);
    this.initTreeData();
    const bizId = this.diffRouteBizId();
    let selectedBiz = Array.from(new Set([...this.selectedBiz, bizId]));
    if (!selectedBiz.every(id => this.bkBizList.find(item => item.bk_biz_id === id))) {
      this.needFix = true;
      selectedBiz = selectedBiz.filter(id => this.bkBizList.find(item => item.bk_biz_id === id));
      MainStore.setSelectedBiz(selectedBiz);
      return;
    }
    if (bizId !== -1 && this.selectedBiz.length && !this.selectedBiz.includes(bizId)) {
      this.needFix = true;
      MainStore.setSelectedBiz(selectedBiz);
    } else {
      this.fixRouteInfo();
    }
  }

  // 进入详情页才缓存界面
  private beforeRouteLeave(to: Route, from: Route, next: () => void) {
    if (to.name === 'resourceQuotaEdit') {
      MainStore.addCachedViews(from);
    } else {
      MainStore.deleteCachedViews(from);
    }
    next();
  }

  // 初始化树所包含的所有业务
  public initTreeData() {
    const allTreeData = getFormatTree(this.bkBizList.map(item => ({
      bk_obj_id: 'biz',
      bk_inst_id: item.bk_biz_id,
      bk_inst_name: item.bk_biz_name,
      id: item.bk_biz_id,
      name: item.bk_biz_name,
      child: [],
    })));
    this.treeSourceList.push(...allTreeData);
    this.treeSourceMap = allTreeData.reduce((obj: Dictionary, item) => {
      obj[item.id] = item;
      return obj;
    }, {});
  }

  // 设置 选中和展开
  public updateTreeStatus() {
    let selectedBiz = [...this.selectedBiz];
    selectedBiz.sort((a, b) => a - b);
    if (!selectedBiz.length) {
      selectedBiz = this.bkBizList.map(item => item.bk_biz_id);
    }
    // 根据业务 展示树
    this.nodeList.splice(0, this.nodeList.length, ...selectedBiz.map(id => this.treeSourceMap[id]));
    let curNode = this.treeSourceMap[this.bizId];
    if (this.moduleId !== -1) {
      curNode = curNode.child.find(item => item.id === this.moduleId) as ITreeNode;
    }
    if (curNode.parent) {
      curNode.parent.folded = true;
    }
    setActiveNode(curNode, this.treeSourceList);
    this.curNode = curNode;
    this.needFix = false;
  }

  // 得到新的bizId
  public diffRouteBizId() {
    let curBizId = this.bizId;
    if (this.hasPageAuth) {
      const selectedBizList: IBkBiz[] = [...this.bkBizList];
      if (curBizId === -1 || !selectedBizList.find(item => item.bk_biz_id === curBizId)) {
        const selectedBiz = [...this.selectedBiz];
        selectedBiz.sort((a, b) => a - b);
        curBizId = selectedBiz.length ? selectedBiz[0] : selectedBizList[0].bk_biz_id;
      }
    }
    return curBizId;
  }

  // 得到新的moduleId
  public async diffRouteModuleId(bizId?: number) {
    const curBizId = bizId || this.bizId;
    let curModuleId = this.moduleId;
    const curRootNode = this.treeSourceMap[curBizId];
    if (curRootNode && !curRootNode.loaded) {
      await this.getTemplatesByBiz(curBizId);
    }
    if (curRootNode?.child?.length) {
      if (curModuleId === -1 || !curRootNode.child.find(child => child.id === curModuleId)) {
        curModuleId = curRootNode.child[0].id;
      }
    } else {
      curModuleId = -1;
    }
    if (curModuleId !== -1) {
      await this.getPluginsConfig(curBizId, curModuleId);
    }

    return Promise.resolve(curModuleId);
  }

  // 修正 选中的biz & 路由的biz和module
  public async fixRouteInfo() {
    if (this.hasPageAuth) {
      const curBizId = this.diffRouteBizId();
      const bizChanged = curBizId !== this.bizId;
      const curModuleId = await this.diffRouteModuleId(curBizId);
      const moduleChanged = curModuleId !== this.moduleId;
      if (bizChanged || moduleChanged) {
        this.needFix = false;
        this.$router.replace({ query: { bizId: `${curBizId}`, moduleId: `${curModuleId}` } });
        return;
      }
      this.updateTreeStatus();
    }
    this.loading = false;
  }

  public async getTemplatesByBiz(bizId: number) {
    const curRootNode = this.treeSourceMap[bizId];
    const templates: IData[] = await PluginStore.getTemplatesByBiz({ bk_biz_id: bizId });
    curRootNode.loaded = true;
    appendChild(curRootNode, templates);
    return Promise.resolve(templates);
  }

  // 拉取单个业务下所有模块的插件配置
  public async getPluginsConfig(bizId?: number, moduleId?: number) {
    this.pluginLoading = true;
    const res = await PluginStore.fetchResourcePolicy({
      bk_biz_id: bizId || this.bizId,
      bk_obj_id: 'service_template',
      bk_inst_id: moduleId || this.moduleId,
    });
    this.pluginList = res.resource_policy;
    this.pluginLoading = false;
    return Promise.resolve(res.resource_policy);
  }

  public async handleTreeSelected(node: ITreeNode) {
    this.curNode = node;
    const bizId = node.type === 'biz' ? node.id : node.parent?.id as number;
    const moduleId = node.type === 'biz' ? -1 : node.id;
    if (moduleId > -1) {
      await this.getPluginsConfig(bizId, moduleId);
    }
    if (this.bizId !== bizId || this.moduleId !== moduleId) {
      this.needFix = false;
      this.$router.replace({ query: { bizId: `${bizId}`, moduleId: `${moduleId}` } });
    }
  }

  public async handleClickNode(node: ITreeNode) {
    // 1、展开/收起 2、选中 3、load&选中
    if (node.loadable) {
      if (!node.loaded) {
        node.loading = true;
        const templates = await this.getTemplatesByBiz(node.id);
        node.loaded = true;
        node.loading = false;
        if (node.foldable) node.folded = true;
        if (!templates.length) {
          this.handleSelected(node);
          return;
        }
      } else {
        if (node.foldable) node.folded = !node.folded;
        // nodeSelectedAble
        if (!node.child?.length && this.curNode?.id !== node.id) {
          this.handleSelected(node);
          return;
        }
      }
    } else {
      if (node.foldable) {
        node.folded = !node.folded;
      } else {
        this.handleSelected(node);
      }
    }
  }

  public handleSelected(node: ITreeNode) {
    setActiveNode(node, this.treeSourceList);
    if (this.curNode?.id !== node.id || this.curNode?.type !== node.type) {
      this.$set(this, 'curNode', node);
      this.handleTreeSelected(node);
    }
  }

  public handleSearchTree() {
    const searchKey = `${this.searchKey}`.toLowerCase();
    this.treeSourceList.forEach((item) => {
      let hasShowChild = false;
      item.child.forEach((child) => {
        const show = `${child.name}`.toLowerCase().includes(searchKey);
        if (show) {
          hasShowChild = true;
        }
        child.show = show;
      });
      item.show = `${item.name}`.toLowerCase().includes(searchKey) || hasShowChild;
    });
  }

  public editResourceQuota() {
    this.$router.push({
      name: 'resourceQuotaEdit',
      query: {
        bizId: `${this.bizId}`,
        moduleId: `${this.moduleId}`,
      },
    });
  }

  public tipsHeadRender(h: CreateElement, { column }: { column: IBkColumn }) {
    const { label, property } = column;
    return h(TableHeader, {
      props: {
        label,
        tips: this.headTipsMap[property as 'cpu' | 'mem'],
        tipTheme: 'light resource-quota-head',
      },
    });
  }

  public handleApplyPermission() {
    bus.$emit('show-permission-modal', {
      params: {
        apply_info: [
          { action: this.action },
          { action: 'plugin_operate' },
        ],
      },
    });
  }

  public handleEmptyLink() {
    const url = `${window.PROJECT_CONFIG.CMDB_URL}/#/business/${this.bizId}/service/template/create`;
    window.open(url, '_blank');
  }
}
</script>

<style lang="postcss" scoped>
.resource-quota {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 52px);
  .page-head {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    flex-shrink: 0;
    padding: 0 16px;
    height: 48px;
    border-bottom: 1px solid #dcdee5;
    background: #fff;
    overflow: hidden;
    .title {
      font-size: 16px;
      color: #313238;
    }
    > span {
      flex-shrink: 0;
    }
  }
  .biz-select-box {
    position: relative;
    height: 32px;
    .biz-placeholder {
      padding-right: 25px;
      pointer-events: none;
      visibility: hidden;
    }
    .biz-text {
      position: absolute;
      top: 0%;
      left: 0;
      right: 25px;
      line-height: 34px;
      background: #fff;
      color: #3A84FF;
      z-index: 50;
      pointer-events: none;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  .biz-select-rimless {
    position: absolute;
    top: 1px;
    left: 0;
    right: 0;
    border-color: transparent;
    &::before {
      color: #fff;
    }
    >>> .icon-angle-down  {
      position: absolute;
      top: 12px;
      right: 6px;
      color: #3A84FF;
      &:before {
        content: "";
        display: block;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #3A84FF;
      }
    }
    &.is-focus {
      box-shadow: none;
    }
    >>> .bk-select-name {
      padding-left: 0;
      padding-right: 25px;
    }
  }
  .dividing-line {
    margin: 0 12px;
    width: 1px;
    height: 16px;
    background: #dcdee5;
  }
  .page-container {
    display: flex;
    flex-direction: column;
    flex: 1;
    .page-tips-wrapper {
      padding: 10px 16px;
      border-bottom: 1px solid #dcdee5;
    }
  }

  .page-body {
    flex: 1;
    display: flex;
    overflow: hidden;
  }
  .side-block {
    display: flex;
    flex-direction: column;
    width: 280px;
    border-right: 1px solid #dcdee5;
    .side-search {
      padding: 15px 16px 10px 16px;
    }
    .resource-tree {
      overflow-y: auto;
    }
  }
  .content-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 20px 24px;
    overflow: hidden;
    .content-body-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 16px;
      color: #313238;
    }
    .content-body-table {
      overflow: hidden;
    }
    .num {
      &.running {
        color: #2DCB56;
      }
      &.abort {
        color: #EA3636;
      }
    }
  }
  .resource-quota-page {
    background: #f5f7fa;
  }
  .template-card {
    margin-top: 100px;
    background: transparent;
  }
}
</style>
