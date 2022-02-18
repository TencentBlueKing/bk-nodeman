<template>
  <article class="resource-quota" v-bkloading="{ isLoading: loading }">
    <section class="page-head">
      <span class="title">{{ $t('资源配额') }}</span>
      <span class="dividing-line"></span>
      <span>{{ $t('业务：') }}</span>
      <div class="biz-select-box">
        <div class="biz-placeholder">{{ bizNames }}</div>
        <bk-biz-select
          v-if="!loading"
          class="biz-select-rimless"
          min-width="50"
          :value="biz"
          @change="handleBizChange">
        </bk-biz-select>
        <div class="biz-text">{{ bizNames }}</div>
      </div>
    </section>
    <section class="page-body">
      <section class="side-block pb20">
        <div class="side-search">
          <bk-input
            :placeholder="$t('请输入关键词')"
            :right-icon="'bk-icon icon-search'"
            v-model="searchKey"
            @change="handleSearchChange">
          </bk-input>
        </div>
        <ResourceTree
          class="resource-tree"
          ref="treeRef"
          :tree-data="treeData"
          :active-id="moduleId"
          :load-method="loadTreeChild"
          @selected="handleTreeSelected">
        </ResourceTree>
      </section>
      <section class="content-body" v-bkloading="{ isLoading: pluginLoading }">
        <div class="content-body-head mb20">
          <p class="content-body-title">{{ moduleName }}</p>
          <bk-button theme="primary" :disabled="moduleId < 0" @click="editResourceQuota">{{ $t('编辑') }}</bk-button>
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
              :label="$t('CPU配额及单位')"
              prop="cpu"
              align="right"
              :resizable="false"
              :render-header="tipsHeadRender" />
            <bk-table-column
              :label="$t('内存配额及单位')"
              prop="mem"
              align="right"
              :resizable="false"
              :render-header="tipsHeadRender" />
            <bk-table-column width="40"></bk-table-column>
          </bk-table>
        </section>
      </section>
    </section>
  </article>
</template>
<script lang="ts">
import { Component, Watch, Mixins, Prop, Ref } from 'vue-property-decorator';
import { MainStore, PluginStore } from '@/store/index';
import ResourceTree from './resource-tree.vue';
import HeaderFilterMixins from '@/components/common/header-filter-mixins';
import { IBkColumn } from '@/types';
import { CreateElement } from 'vue';
import TableHeader from '@/components/setup-table/table-header.vue';
import { debounce } from '@/common/util';

interface ITreeNode {
  id: number
  name: string
  loading: boolean
  active: boolean
  topoType: string
  level: number
  foldable: boolean
  folded: boolean
  child: ITreeNode[]
  parent: ITreeNode
}

@Component({
  name: 'resource-quota',
  components: {
    ResourceTree,
    TableHeader,
  },
})
export default class ResourceQuota extends Mixins(HeaderFilterMixins) {
  @Prop({ type: Number, default: -1 }) private readonly bizId!: number;
  @Prop({ type: Number, default: -1 }) private readonly moduleId!: number;
  @Ref('treeRef') private readonly treeRef!: any;

  public loading = true;
  public pluginLoading = false;
  public curNode: ITreeNode | null = null;
  public searchKey = '';
  public treeData: any[] = [];
  public pluginListMap: any = {};
  public pluginList: any[] = [];
  public headTipsMap = {
    cpu: this.$t('限制最高CPU使用率'),
    ram: this.$t('限制最高内存使用率'),
  };
  public biz: number[] = [];
  public handleSearchChange!: Function;
  public handleBizOrModuleChange!: Function;

  private get moduleName() {
    return this.curNode ? this.curNode.name : '';
  }
  private get windowHeight() {
    return MainStore.windowHeight;
  }
  private get selectedBiz() {
    return MainStore.selectedBiz;
  }
  private get bkBizList() {
    return MainStore.bkBizList;
  }
  private get bkBizNameMap() {
    const nameMap: any = {};
    this.bkBizList.reduce((maps, item) => {
      maps[item.bk_biz_id] = item.bk_biz_name;
      return maps;
    }, nameMap);
    return nameMap;
  }
  private get bizNames() {
    if (this.biz.length) {
      return this.biz.map(id => this.bkBizNameMap[id]).join('、');
    }
    return this.$t('全部业务');
  }

  @Watch('bizId')
  public handleRouteBizChange() {
    this.handleBizOrModuleChange();
  }
  @Watch('moduleId')
  public handleRouteModuleChange() {
    this.handleBizOrModuleChange();
  }

  private async created() {
    this.handleBizOrModuleChange = debounce(300, this.replaceBizAndModule);
    this.handleSearchChange = debounce(300, this.handleSearchTree);
  }
  private async mounted() {
    this.replaceBizAndModule();
  }

  /**
   * 找到当前业务及业务下的模板，否则跳到第一个业务下的第一个模块
   */
  public async replaceBizAndModule() {
    const hasAuthBizList = this.bkBizList.filter(item => !item.disabled);
    if (hasAuthBizList.length) {
      const loadBizId = this.bizId > -1 && hasAuthBizList.find(item => item.bk_biz_id === this.bizId)
        ? this.bizId : hasAuthBizList[0].bk_biz_id;
      // 初始化选中业务
      this.biz = this.selectedBiz.length ? Array.from(new Set([...this.selectedBiz, loadBizId])) : [];

      // 设置业务列表 && 树
      const selectedBizList = this.biz.length
        ? hasAuthBizList.filter(item => this.biz.includes(item.bk_biz_id))
        : hasAuthBizList;
      const curTreeData = this.treeData.reduce((obj, item) => {
        obj[item.bk_inst_id] = item;
        return obj;
      }, {});
      // 保存已经加载过的业务
      this.treeData = selectedBizList.map((item) => {
        if (curTreeData[item.bk_biz_id]) {
          return curTreeData[item.bk_biz_id];
        }
        return {
          bk_obj_id: 'biz',
          bk_inst_id: item.bk_biz_id,
          bk_inst_name: item.bk_biz_name,
          child: [],
        };
      });
      // 拿到moduleId进一步判断是否需要重定向路由
      let children: any[] = [];
      const loadedParent = this.treeData.find(item => item.bk_inst_id === loadBizId && item.child.length);
      if (loadedParent) {
        children = loadedParent.child;
      } else {
        children = await this.getTemplatesByBiz(loadBizId);
      }
      this.$nextTick(() => {
        this.treeRef && this.treeRef.setTreeData();
      });

      let loadModuleId = -1;
      if (children.length) {
        loadModuleId = this.moduleId > -1 && children.find(item => item.bk_inst_id === this.moduleId)
          ? this.moduleId
          : children[0].bk_inst_id;
      }
      if (this.bizId !== loadBizId || (this.moduleId !== loadModuleId)) {
        const query: any = {
          bizId: loadBizId,
        };
        if (loadModuleId > -1) {
          query.moduleId = loadModuleId;
        }
        this.$router.replace({ query });
      }
      this.loading = false;
    }
  }

  public async getTemplatesByBiz(bizId?: number) {
    const id = bizId || this.bizId;
    const templates: any[] = await PluginStore.getTemplatesByBiz({ bk_biz_id: id });
    const templatesStatus: any[] = await PluginStore.fetchResourcePolicyStatus({ bk_biz_id: id, bk_obj_id: 'service_template' });
    // 是否调整过插件配置
    templates.forEach((item) => {
      item.topoIcon = templatesStatus.find(template => template.bk_inst_id === item.bk_inst_id && !template.is_default);
    });
    const parent = this.treeData.find(item => item.bk_inst_id === bizId);
    parent?.child.push(...templates);
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
  }

  public handleBizChange(value: number[]) {
    const oldBiz = [...this.biz];
    this.biz = value;
    if (oldBiz.length !== value.length || oldBiz.some(old => value.find(id => old !== id))) {
      this.replaceBizAndModule();
    }
  }

  public handleTreeSelected(node: ITreeNode) {
    if (!this.curNode || node.id !== this.curNode.id) {
      this.curNode = node;
      this.$router.replace({ query: { bizId: `${node.parent.id}`, moduleId: `${node.id}` } });
      this.getPluginsConfig(node.parent.id, node.id);
    }
  }

  public handleSearchTree() {
    if (this.treeRef) {
      this.treeRef.search(this.searchKey);
    }
  }

  public async loadTreeChild(node: ITreeNode) {
    const templates = await this.getTemplatesByBiz(node.id);
    return Promise.resolve(templates);
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
        tips: this.headTipsMap[property as 'cpu' | 'ram'],
      },
    });
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
}
</style>
