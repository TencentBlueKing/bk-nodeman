<template>
  <ResourceTreeItem
    :node-list="nodeList"
    @click="handleClickNode">
  </ResourceTreeItem>
</template>

<script lang="ts">
import { Prop, Vue, Component } from 'vue-property-decorator';
import ResourceTreeItem from './resource-tree-item.vue';

export type INodeType = 'biz' | 'template';

export interface IData {
  bk_inst_id: number
  bk_inst_name: string
  bk_obj_id: INodeType
  bk_biz_id?: number
  topoIcon?: boolean
  child?: IData[]
}

export interface ITreeNode {
  id: number
  name: string
  type: INodeType
  active: boolean
  show: boolean
  level: number
  loadable: boolean
  loaded: boolean
  loading: boolean
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

  @Prop({ type: String, default: -1 }) private readonly activeId!: number;
  @Prop({ type: Object }) private readonly selectedNode!: ITreeNode | null;
  @Prop({ type: Array, default: () => [] }) private readonly treeData!: IData[];
  // @Prop({ type: String, default: 'left' }) private readonly loadPosition!: string;
  @Prop({ type: Function }) private readonly loadMethod!: Function;
  @Prop({ type: Function }) private readonly nodeShowAble?: (node: Dictionary) => boolean;
  @Prop({ type: Function }) private readonly nodeLoadAble?: (node: Dictionary) => boolean;
  @Prop({ type: Function }) private readonly nodeFoldAble?: (node: Dictionary) => boolean;
  @Prop({ type: Function }) private readonly nodeSelectedAble?: (node: Dictionary) => boolean;

  private activeNode: ITreeNode | null = null;

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
    const node = this.findCurrentNode();
    if (node) {
      this.toggleExpandedParent(node, true);
      this.scrollToActiveNode();
      this.handleSelected(node);
    }
  }

  public async handleClickNode(node: ITreeNode) { // 1、展开/收起 2、选中 3、load&选中
    if (node.loadable) {
      if (!node.loaded) {
        if (!this.loadMethod) {
          console.error('loadMethod is required.');
          return;
        }
        node.loading = true;
        const children = await this.loadMethod(node);
        node.loaded = true;
        node.loading = false;
        if (node.foldable) node.folded = true;
        if (children.length) {
          this.appendChild(node, children);
        } else {
          this.handleSelected(node);
          return;
        }
      } else {
        if (node.foldable) node.folded = !node.folded;
        // nodeSelectedAble
        if (!node.child?.length && this.activeNode?.id !== node.id) {
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
    this.setActiveNode(node);
    this.$set(this, 'activeNode', node);
    this.$emit('selected', node);
  }

  public async appendChild(parent: ITreeNode, nodes: any[]) {
    parent.child.splice(parent.child.length, 0, ...nodes.map(item => this.formatTreeNode(item, 1, parent)));
  }

  public toggleExpandedParent(node: ITreeNode, expanded?: boolean) {
    if (node.parent) {
      if (node.parent.foldable) {
        node.parent.folded = !!expanded;
      }
      this.toggleExpandedParent(node.parent, expanded);
    }
  }

  public getFormatTree(list: IData[], level = 0, parent?: ITreeNode) {
    return list.map(item => this.formatTreeNode(item, level, parent));
  }

  public formatTreeNode(item: IData, level = 0, parent?: ITreeNode): ITreeNode {
    const node: ITreeNode = {
      ...item,
      id: item.bk_inst_id,
      name: `${item.bk_inst_name}`,
      type: item.bk_obj_id,
      level,
      active: false,
      topoIcon: !!item.topoIcon,
      show: this.nodeShowAble?.(item) || true,
      loadable: this.nodeLoadAble?.(item) || false,
      loaded: !!item.child?.length || false,
      loading: false,
      foldable: this.nodeFoldAble?.(item) || false,
      folded: false,
      parent,
      child: [],
    };
    node.child = item.child && item.child.length ? this.getFormatTree(item.child, level + 1, node) : [];
    return node;
  }

  public setActiveNode(node: ITreeNode) {
    const targetNode = this.findNode(node);
    if (targetNode) {
      const curActiveNode = this.findCurrentNode();
      if (curActiveNode) {
        curActiveNode.active = false;
      }
      targetNode.active = true;
    }
  }

  public findCurrentNode(node?: ITreeNode): ITreeNode | undefined {
    return this.findNode(node || this.selectedNode as ITreeNode);
  }

  public findNode(node: { id: number, type: string }, list?: ITreeNode[]): ITreeNode | undefined {
    let curNode: ITreeNode | undefined = undefined;
    (list || this.nodeList).forEach((item) => {
      if (item.id === node.id && item.type === node.type) {
        curNode = item;
      }
      if (!curNode && item.child && item.child.length) {
        curNode = this.findNode(node, item.child);
      }
    });
    return curNode;
  }


  public search(key: string) {
    const searchKey = `${key}`.toLowerCase();
    this.nodeList.forEach((item) => {
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

  public scrollToActiveNode() {
    this.$nextTick(() => {
      const { top, bottom } = this.$el.getBoundingClientRect();
      const ele = document.querySelector('div[class="tree-node-item topo-active"]');
      if (ele) {
        const { height: itemHeight, top: itemTop, bottom: itemBottom } = ele.getBoundingClientRect();
        if (top > itemTop || bottom < itemBottom - itemHeight) {
          ele.scrollIntoView();
        }
      }
    });
  }
}
</script>
