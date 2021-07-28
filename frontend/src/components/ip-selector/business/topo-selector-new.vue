<template>
  <ip-selector
    ref="selector"
    class="ip-selector"
    :key="selectorKey"
    :panels="panels"
    :height="height"
    :active.sync="active"
    :preview-data="previewData"
    :get-default-data="handleGetDefaultData"
    :get-search-table-data="handleGetSearchTableData"
    :dynamic-table-config="dynamicTableConfig"
    :static-table-config="staticTableConfig"
    :template-table-config="templateTableConfig"
    :cluster-table-config="templateTableConfig"
    :custom-input-table-config="staticTableConfig"
    :get-default-selections="getDefaultSelections"
    :preview-operate-list="previewOperateList"
    :service-template-placeholder="$t('搜索模块名')"
    :cluster-template-placeholder="$t('搜索集群名')"
    :preview-width="previewWidth"
    :default-checked-nodes="defaultCheckedNodes"
    @check-change="handleCheckChange"
    @remove-node="handleRemoveNode"
    @menu-click="handleMenuClick">
  </ip-selector>
</template>
<script lang="ts">
/* eslint-disable camelcase */
import { Vue, Component, Prop, Ref, Watch, Emit } from 'vue-property-decorator';
import IpSelector from '../index.vue';
import AgentStatus from '../components/agent-status.vue';
import {
  IPanel,
  ITableConfig,
  IPreviewData,
  IMenu, ITableCheckData, IpType,
} from '../types/selector-type';
import { defaultSearch } from '../common/util';
import {
  getTopoTree,
  getTemplate,
  getNodesByTemplate,
  getHostInstanceByIp,
  getServiceInstanceByNode,
  getHostInstanceByNode,
} from '../../../../monitor-api/modules/commons';

@Component({
  name: 'topo-selector',
  components: {
    IpSelector,
  },
})
export default class TopoSelector extends Vue {
  @Prop({ default: 'INSTANCE' }) private readonly targetNodeType!: IpType;
  @Prop({ default: 'HOST' }) private readonly targetObjectType!: 'HOST' | 'SERVICE';
  @Prop({ default: () => [], type: Array }) private readonly checkedData!: any[];
  @Prop({ default: 280, type: Number }) private readonly previewWidth!: number;
  @Prop({ default: false }) private readonly hiddenTopo!: boolean;
  @Prop({ default: 460, type: [Number, String] }) private readonly height!: number |  string;
  @Prop({ default: false, type: Boolean }) private readonly withExternalIps!: boolean;

  @Ref('selector') private readonly selector!: IpSelector;

  // 当前激活tab
  private active = '';
  // topo树数据
  private topoTree: any[] = [];
  private ipNodesMap: any = {};
  // 动态拓扑表格数据
  private topoTableData: any[] = [];
  // 动态TOPO树默认勾选数据
  private defaultCheckedNodes: (string | number)[] = [];
  // 静态表格数据
  private staticTableData: any[] = [];
  // 动态拓扑表格配置
  private dynamicTableConfig: ITableConfig[] = [];
  // 静态拓扑表格配置
  private staticTableConfig: ITableConfig[] = [];
  // 模板拓扑配置
  private templateTableConfig: ITableConfig[] = [];
  // 预览数据
  private previewData: IPreviewData[] = [];
  // 更多操作配置
  private previewOperateList: IMenu[] = [];
  // v-if方式渲染选择器时需要重置Key
  private selectorKey = 1;
  // 节点类型和实际IP选择类型的映射关系
  private nodeTypeMap = {
    TOPO: 'dynamic-topo',
    INSTANCE: 'static-topo',
    SERVICE_TEMPLATE: 'service-template',
    SET_TEMPLATE: 'cluster',
  };

  private get isInstance() {
    // 采集对象为服务时，只能选择动态
    return this.targetObjectType === 'SERVICE';
  }

  private get panels(): IPanel[] {
    const panels: IPanel[] = [
      {
        name: 'dynamic-topo',
        label: this.$t('动态拓扑'),
        tips: this.$t('不能混用'),
        disabled: false,
        type: 'TOPO',
        hidden: this.hiddenTopo,
      },
      {
        name: 'static-topo',
        label: this.$t('静态拓扑'),
        hidden: this.isInstance,
        tips: this.$t('不能混用'),
        disabled: false,
        type: 'INSTANCE',
      },
      {
        name: 'service-template',
        label: this.$t('服务模板'),
        tips: this.$t('不能混用'),
        disabled: false,
        type: 'TOPO',
        hidden: this.hiddenTopo,
      },
      {
        name: 'cluster',
        label: this.$t('集群模板'),
        tips: this.$t('不能混用'),
        disabled: false,
        type: 'TOPO',
        hidden: this.hiddenTopo,
      },
      {
        name: 'custom-input',
        label: this.$t('自定义输入'),
        hidden: this.isInstance,
        tips: this.$t('不能混用'),
        disabled: false,
        type: 'INSTANCE',
      },
    ];
    const dynamicType = ['TOPO', 'SERVICE_TEMPLATE', 'SET_TEMPLATE'];
    const isDynamic = this.previewData.some(item => dynamicType.includes(item.id) && item.data.length);
    const isStatic = this.previewData.some(item => item.id === 'INSTANCE' && item.data.length);
    return panels.map((item) => {
      item.disabled = (item.name !== this.active && isDynamic) || (item.type === 'TOPO' && isStatic);
      return item;
    });
  }

  @Watch('active')
  private handleActiveChange() {
    this.staticTableData = [];
    this.topoTableData = [];
  }

  @Watch('targetNodeType', { immediate: true })
  private handleDefaultActiveChange() {
    if (this.nodeTypeMap[this.targetNodeType]) {
      this.active = this.nodeTypeMap[this.targetNodeType];
    } else {
      const panel =  this.panels.find(item => !item.disabled && !item.hidden);
      this.active = panel ? panel.name : 'static-topo';
    }
  }

  @Watch('checkedData', { immediate: true })
  private handleCheckedDataChange() {
    if (this.checkedData && this.checkedData.length) {
      const nodeTypeTextMap = {
        TOPO: this.$t('节点'),
        INSTANCE: this.$t('IP'),
        SERVICE_TEMPLATE: this.$t('服务模板'),
        SET_TEMPLATE: this.$t('集群模板'),
      };
      const nodeTypeNameMap = {
        TOPO: 'bk_inst_name',
        INSTANCE: 'ip',
        SERVICE_TEMPLATE: 'bk_inst_name',
        SET_TEMPLATE: 'bk_inst_name',
      };
      this.previewData = [];
      this.previewData.push({
        id: this.targetNodeType,
        name: nodeTypeTextMap[this.targetNodeType] || '--',
        data: [...this.checkedData],
        dataNameKey: nodeTypeNameMap[this.targetNodeType],
      });
      this.targetNodeType === 'TOPO' && this.handleSetDefaultCheckedNodes();
    }
  }

  private created() {
    this.previewOperateList = [
      {
        id: 'removeAll',
        label: this.$t('移除所有'),
      },
    ];
    this.dynamicTableConfig = [
      {
        prop: 'node_path',
        label: this.$t('子节点名称'),
      },
      {
        prop: 'status',
        label: this.$t('Agent状态'),
        render: this.renderAgentCountStatus,
      },
    ];
    this.templateTableConfig = [
      {
        prop: 'node_path',
        label: this.$t('节点名称'),
      },
      {
        prop: 'status',
        label: this.$t('Agent状态'),
        render: this.renderAgentCountStatus,
      },
    ];
    this.staticTableConfig = [
      {
        prop: 'ip',
        label: 'IP',
      },
      {
        prop: 'agent_status',
        label: this.$t('Agent状态'),
        render: this.renderIpAgentStatus,
      },
      {
        prop: 'bk_cloud_name',
        label: this.$t('云区域'),
      },
      {
        prop: 'bk_os_type',
        label: this.$t('操作系统'),
      },
    ];
  }
  private renderIpAgentStatus(row: any) {
    const textMap = {
      normal: this.$t('正常'),
      abnormal: this.$t('异常'),
      not_exist: this.$t('未安装'),
    };
    const statusMap = {
      normal: 'running',
      abnormal: 'terminated',
      not_exist: 'unknown',
    };
    return this.$createElement(AgentStatus, {
      props: {
        type: 1,
        data: [
          {
            status: statusMap[row.agent_status],
            count: row.agent_error_count,
            display: textMap[row.agent_status],
          },
        ],
      },
    });
  }
  private renderAgentCountStatus(row: any) {
    return this.$createElement(AgentStatus, {
      props: {
        type: 3,
        data: [
          {
            count: row.count,
            errorCount: row.agent_error_count,
          },
        ],
      },
    });
  }

  // 获取当前tab下默认数据
  private async handleGetDefaultData() {
    if (['dynamic-topo', 'static-topo'].includes(this.active)) {
      // 动态拓扑默认组件数据
      if (!this.topoTree.length) {
        const data = await this.getTopoTree();
        this.topoTree = this.removeIpNodes(data);
        this.active === 'dynamic-topo' && this.handleSetDefaultCheckedNodes();
      }
      return [
        {
          name: this.$t('根节点'),
          children: this.topoTree,
        },
      ];
    }
    if (['service-template', 'cluster'].includes(this.active)) {
      const data = await getTemplate({
        bk_inst_type: this.isInstance ? 'SERVICE' : 'HOST',
        bk_obj_id: this.active === 'cluster' ? 'SET_TEMPLATE' : 'SERVICE_TEMPLATE',
        with_count: true,
      }).catch(() => ({ children: [] }));
      return data.children;
    }
  }
  private handleSetDefaultCheckedNodes() {
    // todo 待优化，多处调用，性能问题
    const { data = [] } = this.previewData.find(item => item.id === 'TOPO') || {};
    this.defaultCheckedNodes = this.getCheckedNodesIds(this.topoTree, data);
  }
  // 获取选中节点的ID集合
  private getCheckedNodesIds(nodes: any[], checkedData: any[] = []) {
    if (!checkedData.length) return [];
    return nodes.reduce<(string | number)[]>((pre, item) => {
      const { children = [], bk_inst_id = '', bk_obj_id = '', id } = item;
      const exist = checkedData.some(checkedData => checkedData.bk_inst_id === bk_inst_id
      && checkedData.bk_obj_id === bk_obj_id);
      if (exist) {
        pre.push(id);
      }
      if (children.length) {
        pre.push(...this.getCheckedNodesIds(children, checkedData));
      }
      return pre;
    }, []);
  }
  // 移除树上的所有IP节点
  private removeIpNodes(data: any[]) {
    data.forEach((item) => {
      const { children = [] } = item;
      if (item.bk_obj_id === 'module' && children.length) {
        this.ipNodesMap[`${item.bk_inst_id}_${item.bk_obj_id}`] = [...item.children];
        item.children = [];
        // item.ipCount = children.length
      } else if (children.length) {
        this.removeIpNodes(item.children);
        // const data = this.removeIpNodes(item.children)
        // data.forEach((child) => {
        //   item.ipCount = (item.ipCount || 0) + (child.ipCount || 0)
        // })
      }
    });
    return data;
  }
  // 获取树节点下所有IP节点
  private getNodesIpList(data: any[]) {
    return data.reduce<any[]>((pre, item) => {
      if (item.bk_obj_id === 'module') {
        const ipNodes = this.ipNodesMap[`${item.bk_inst_id}_${item.bk_obj_id}`] || [];
        pre.push(...ipNodes);
      } else if (item.children && item.children.length) {
        pre.push(...this.getNodesIpList(item.children));
      }
      return pre;
    }, []);
  }
  // 获取表格数据（组件内部封装了交互逻辑）
  private async handleGetSearchTableData(params: any, type?: string): Promise<{
    total: number, data: any[] }> {
    if (this.active === 'dynamic-topo') {
      return await this.getDynamicTopoTableData(params, type);
    }
    if (this.active === 'static-topo') {
      return await this.getStaticTableData(params, type);
    }
    if (['service-template', 'cluster'].includes(this.active)) {
      return await this.getTemplateTableData(params);
    }
    if (this.active === 'custom-input') {
      return await this.getCustomInputTableData(params);
    }
    return {
      total: 0,
      data: [],
    };
  }
  // 获取动态topo表格数据
  private async getDynamicTopoTableData(params: any, type?: string) {
    let data = [];
    if (type === 'selection-change') {
      const { selections = [] } = params;
      if (!!selections.length) {
        this.topoTableData = this.targetObjectType === 'SERVICE'
          ? await getServiceInstanceByNode({ node_list: selections }).catch(() => [])
          : await getHostInstanceByNode({ node_list: selections }).catch(() => []);
        data = this.topoTableData;
      }
    } else {
      const { tableKeyword = '' } = params;
      data = defaultSearch(this.topoTableData, tableKeyword);
    }

    return {
      total: data.length,
      data,
    };
  }
  // 获取静态表格数据
  private async getStaticTableData(params: any, type?: string) {
    let data = [];
    if (type === 'selection-change') {
      const { selections = [] } = params;
      console.log(selections);
      if (!!selections.length) {
        const ipNodes = this.getNodesIpList(selections).reduce<any[]>((pre, next) => {
          // IP去重
          const index = pre.findIndex(item => this.identityIp(item, next));
          index === -1 && pre.push(next);
          return pre;
        }, []);
        this.staticTableData = await getHostInstanceByIp({
          ip_list: ipNodes.map((item) => {
            const { ip, bk_cloud_id } = item;
            return {
              ip,
              bk_cloud_id,
            };
          }),
        }).catch(() => []);
        data = this.staticTableData;
      }
    } else {
      const { tableKeyword = '' } = params;
      data = defaultSearch(this.staticTableData, tableKeyword);
    }

    return {
      total: data.length,
      data,
    };
  }
  // 获取模板类表格数据
  private async getTemplateTableData(params: any) {
    const { selections = [] } = params;
    let data = [];
    if (!!selections.length) {
      data = await getNodesByTemplate({
        bk_inst_type: this.isInstance ? 'SERVICE' : 'HOST',
        bk_obj_id: this.active === 'cluster' ? 'SET_TEMPLATE' : 'SERVICE_TEMPLATE',
        bk_inst_ids: selections.map(item => item.bk_inst_id),
      }).catch(() => []);
    }
    return {
      total: data.length,
      data,
    };
  }
  // 获取自定义输入表格数据
  private async getCustomInputTableData(params: any) {
    const { ipList = [] } = params;
    const data = await getHostInstanceByIp({
      ip_list: ipList.map(ip => ({ ip })),
      with_external_ips: this.withExternalIps,
    }).catch(() => []);
    return {
      total: data.length,
      data,
    };
  }

  // topo树数据
  private async getTopoTree() {
    const params: any = {
      instance_type: 'host',
    };
    return await getTopoTree(params).catch(() => []);
  }
  // 表格check表更事件(请勿修改selectionsData里面的数据)
  @Emit('check-change')
  private handleCheckChange(selectionsData: ITableCheckData) {
    if (this.active === 'dynamic-topo') {
      this.dynamicTableCheckChange(selectionsData);
      this.handleSetDefaultCheckedNodes();
    }
    if (['service-template', 'cluster'].includes(this.active)) {
      this.templateCheckChange(selectionsData);
    }
    if (['static-topo', 'custom-input'].includes(this.active)) {
      this.staticIpTableCheckChange(selectionsData);
    }
    return this.getCheckedData();
  }
  // 模板类型check事件
  private templateCheckChange(selectionsData: ITableCheckData) {
    const { selections = [] } = selectionsData;
    const type = this.active === 'service-template' ? 'SERVICE_TEMPLATE' : 'SET_TEMPLATE';
    const index = this.previewData.findIndex(item => item.id === type);
    if (index > -1) {
      this.previewData[index].data = [...selections];
    } else {
      // 初始化分组信息(模板类型都属于动态拓扑)
      this.previewData.push({
        id: type,
        name: this.active === 'service-template' ? this.$t('服务模板') : this.$t('集群模板'),
        data: [...selections],
        dataNameKey: 'name',
      });
    }
  }
  // 动态类型表格check事件
  private dynamicTableCheckChange(selectionsData: ITableCheckData) {
    const { selections = [], excludeData = [] } = selectionsData;
    const index = this.previewData.findIndex(item => item.id === 'TOPO');
    if (index > -1) {
      const { data } = this.previewData[index];
      selections.forEach((select) => {
        const index = data.findIndex(data => (data.bk_inst_id === select.bk_inst_id)
          && (data.bk_obj_id === select.bk_obj_id));

        index === -1 && data.push(select);
      });
      excludeData.forEach((exclude) => {
        const index = data.findIndex(data => (data.bk_inst_id === exclude.bk_inst_id)
          && (data.bk_obj_id === exclude.bk_obj_id));

        index > -1 && data.splice(index, 1);
      });
    } else {
      // 初始化分组信息
      this.previewData.push({
        id: 'TOPO',
        name: this.$t('节点'),
        data: [...selections],
        dataNameKey: 'bk_inst_name',
      });
    }
  }
  // 静态类型的表格check事件
  private staticIpTableCheckChange(selectionsData: ITableCheckData) {
    const { selections = [], excludeData = [] } = selectionsData;
    const index = this.previewData.findIndex(item => item.id === 'INSTANCE');
    if (index > -1) {
      const { data } = this.previewData[index];
      selections.forEach((select) => {
        const index = data.findIndex(data => this.identityIp(data, select));

        index === -1 && data.push(select);
      });
      excludeData.forEach((exclude) => {
        const index = data.findIndex(data => this.identityIp(data, exclude));

        index > -1 && data.splice(index, 1);
      });
    } else {
      // 初始化分组信息
      this.previewData.push({
        id: 'INSTANCE',
        name: this.$t('IP'),
        data: [...selections],
        dataNameKey: 'ip',
      });
    }
  }

  // 移除节点
  @Emit('check-change')
  private handleRemoveNode({ child, item }: { child: any, item: IPreviewData }) {
    const group = this.previewData.find(data => data.id === item.id);
    if (group) {
      const index = group.data.findIndex((data) => {
        if (group.id === 'TOPO') {
          return (data.bk_inst_id === child.bk_inst_id) && (data.bk_obj_id === child.bk_obj_id);
        } if (group.id === 'INSTANCE') {
          return this.identityIp(data, child);
        }
        return data.bk_inst_id === child.bk_inst_id;
      });
      index > -1 && group.data.splice(index, 1);
    }
    this.selector.handleGetDefaultSelections();
    item.id === 'TOPO' && this.handleSetDefaultCheckedNodes();
    return this.getCheckedData();
  }
  // 当前check项
  private getDefaultSelections(row: any) {
    if (this.active === 'dynamic-topo') {
      const group = this.previewData.find(data => data.id === 'TOPO');
      return group?.data.some(data => (data.bk_inst_id === row.bk_inst_id)
          && (data.bk_obj_id === row.bk_obj_id));
    }
    if (['static-topo', 'custom-input'].includes(this.active)) {
      const group = this.previewData.find(data => data.id === 'INSTANCE');
      return group?.data.some(data => this.identityIp(data, row));
    }
    if (['service-template', 'cluster'].includes(this.active)) {
      const type = this.active === 'service-template' ? 'SERVICE_TEMPLATE' : 'SET_TEMPLATE';
      const group = this.previewData.find(data => data.id === type);
      return group?.data.some(data => data.bk_inst_id === row.bk_inst_id);
    }
    return false;
  }
  // 预览菜单点击事件
  private handleMenuClick({ menu, item }: { menu: IMenu, item: IPreviewData }) {
    if (menu.id === 'removeAll') {
    //   const group = this.previewData.find(data => data.id === item.id)
    //   group && (group.data = [])
      const index = this.previewData.findIndex(data => data.id === item.id);
      index > -1 && this.previewData.splice(index, 1);
      this.selector.handleGetDefaultSelections();
      item.id === 'TOPO' && this.handleSetDefaultCheckedNodes();
      this.$emit('check-change', this.getCheckedData());
    }
  }
  // 获取勾选的数据
  private getCheckedData() {
    // 默认只能选择一种方式
    const previewData = this.previewData.filter(item => item.data && item.data.length);
    const [group] = previewData;
    if (previewData.length !== 1 || group.data.length === 0) return { type: this.targetNodeType, data: [] };
    return {
      type: group.id,
      data: group.data,
    };
  }
  // 判断IP是否一样
  private identityIp(pre, next) {
    // 有云区域id时，云区域ID加IP唯一标识一个IP，没有云区域时IP作为唯一ID
    return (Object.prototype.hasOwnProperty.call(pre, 'bk_cloud_id')
      ? (pre.ip === next.ip) && (pre.bk_cloud_id === next.bk_cloud_id)
      : pre.ip === next.ip);
  }
  private resize() {
    this.$nextTick(() => {
      this.selectorKey = Math.random() * 10;
    });
  }
}
</script>
<style lang="scss" scoped>
.ip-selector {
  min-width: 600px;
}
</style>
