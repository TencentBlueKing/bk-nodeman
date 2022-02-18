<template>
  <ResourceTreeItem
    :node-list="nodeList"
    :load-position="loadPosition"
    @click="handleClickNode">
  </ResourceTreeItem>
</template>

<script lang="ts">
import { Prop, Vue, Component } from 'vue-property-decorator';
import ResourceTreeItem from './resource-tree-item.vue';

interface ITreeNode {
  id: string | number
  name: string
  loaded: boolean,
  loading: boolean
  active: boolean
  topoType: 'biz' | 'module'
  show: boolean
  level: number
  foldable: boolean
  folded: boolean
  child: ITreeNode[]
  topoIcon: boolean
  parent?: ITreeNode
}
interface ITreeId {
  id?: string | number
  key: keyof ITreeNode
  value: string | number | boolean | ITreeNode[]
  list?: ITreeNode[]
}

@Component({
  name: 'ResourceTree',
  components: { ResourceTreeItem },
})
export default class ResourceTree extends Vue {
  public nodeList: ITreeNode[] = [];

  @Prop({ type: String, default: '' }) private readonly activeId!: number;
  @Prop({ type: Array, default: () => [] }) private readonly treeData!: any[];
  @Prop({ type: String, default: 'left' }) private readonly loadPosition!: string;
  @Prop({ type: Function }) private readonly loadMethod!: Function;

  private created() {
    this.$set(this, 'nodeList', this.getFormatTree(this.treeData));
  }

  private setTreeData() {
    const curNodeMap = this.nodeList.reduce((obj: any, parent) => {
      obj[`${parent.id}`] = parent;
      return obj;
    }, {});
    const nodeList = this.getFormatTree(this.treeData).map((item) => {
      if (curNodeMap[item.id]) {
        return curNodeMap[item.id];
      }
      return item;
    });
    this.$set(this, 'nodeList', nodeList);
    this.initActiveNode();
  }

  /**
   * 默认选中一个节点
   */
  public initActiveNode() {
    const node = this.findNode(this.activeId);
    if (node) {
      this.$emit('selected', node);
      this.setActiveNode({ key: 'id', value: node.id });
      this.toggleExpandedParent(node, true);
      this.$nextTick(() => {
        const ele = document.querySelector('div[class="tree-node-item topo-active"]');
        ele?.scrollIntoView();
      });
    }
  }

  public async handleClickNode(node: ITreeNode) {
    if (node.topoType === 'biz') {
      if (!node.loaded && !!this.loadMethod) {
        node.loading = true;
        const children = await this.loadMethod(node);
        this.appendChild(node, children);
        node.loaded = true;
        node.loading = false;
      }
      node.folded = !node.folded;
    } else {
      this.setActiveNode({ key: 'id', value: node.id });
      this.$emit('click', node);
      this.$emit('selected', node);
    }
  }

  public async appendChild(parent: ITreeNode, nodes: any[]) {
    parent.child.splice(parent.child.length, 0, ...nodes.map(item => this.getFormatNode(item, 1, parent)));
  }

  public toggleExpandedParent(node: ITreeNode, expanded?: boolean) {
    if (node.parent) {
      if (node.parent.foldable) {
        node.parent.folded = !!expanded;
      }
      this.toggleExpandedParent(node.parent, expanded);
    }
  }

  public getFormatTree(list: any[], level = 0, parent?: ITreeNode) {
    return list.map(item => this.getFormatNode(item, level, parent));
  }

  public getFormatNode(item: any, level = 0, parent?: ITreeNode): ITreeNode {
    const node: ITreeNode = {
      id: item.bk_inst_id,
      name: `${item.bk_inst_name}`,
      loading: false,
      loaded: item.bk_obj_id === 'biz' ? !!(item.child && item.child.length) : true,
      active: false,
      level,
      topoType: item.bk_obj_id,
      show: true,
      foldable: item.bk_obj_id === 'biz',
      folded: false,
      child: [],
      topoIcon: item.topoIcon,
      parent,
    };
    node.child = item.child && item.child.length ? this.getFormatTree(item.child, level + 1, node) : [];
    return node;
  }
  public setActiveNode(params: ITreeId) {
    const targetNode = this.findNodeAttr(params);
    if (targetNode) {
      const curActiveNode = this.findNodeAttr({ key: 'active', value: true });
      if (curActiveNode) {
        curActiveNode.active = false;
      }
      targetNode.active = true;
    }
  }

  public findNode(id: string | number): ITreeNode | undefined {
    return this.findNodeAttr({ key: 'id', value: id });
  }

  public findNodeAttr({ key, value, list }: ITreeId): ITreeNode | undefined {
    let node: ITreeNode | undefined = undefined;
    (list || this.nodeList).forEach((item) => {
      if (item[key] === value) {
        node = item;
      }
      if (!node && item.child && item.child.length) {
        node = this.findNodeAttr({ key, value, list: item.child });
      }
    });
    return node;
  }

  public setNodeAttr(params: ITreeId) {
    if (params.id) {
      const targetNode = this.findNode(params.id);
      if (targetNode) {
        this.$set(targetNode, params.key, params.value);
      }
    }
  }

  public search(key: string) {
    const searchKey = `${key}`;
    this.nodeList.forEach((item) => {
      let hasShowChild = false;
      item.child.forEach((child) => {
        const show = child.name.includes(searchKey);
        if (show) {
          hasShowChild = true;
        }
        child.show = show;
      });
      item.show = item.name.includes(searchKey) || hasShowChild;
    });
  }
}
</script>
