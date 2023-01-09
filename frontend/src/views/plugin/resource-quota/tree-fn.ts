export type INodeType = 'biz' | 'template';

export interface IData {
  bk_inst_id: number
  bk_inst_name: string
  bk_obj_id: INodeType
  bk_biz_id?: number
  topoIcon?: boolean
  loaded?: boolean
  folded?: boolean
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

export function nodeShowAble() {
  return true;
}

export function nodeLoadAble(item: IData) {
  return item.bk_obj_id === 'biz';
}
export function nodeFoldAble(item: IData) {
  return item.bk_obj_id === 'biz';
}

export function getFormatTree(list: IData[], level = 0, parent?: ITreeNode) {
  return list.map(item => formatTreeNode(item, level, parent));
}

export function formatTreeNode(item: IData, level = 0, parent?: ITreeNode): ITreeNode {
  const node: ITreeNode = {
    ...item,
    id: item.bk_inst_id,
    name: `${item.bk_inst_name}`,
    type: item.bk_obj_id,
    level,
    active: false,
    topoIcon: !!item.topoIcon,
    show: nodeShowAble?.(item) || true,
    loadable: nodeLoadAble?.(item) || false,
    loaded: item.loaded || !!item.child?.length || false,
    loading: false,
    foldable: nodeFoldAble?.(item) || false,
    folded: item.loaded || false,
    parent,
    child: [],
  };
  node.child = item.child && item.child.length ? getFormatTree(item.child, level + 1, node) : [];
  return node;
}

export async function appendChild(parent: ITreeNode, nodes: IData[]) {
  parent.child.splice(parent.child.length, 0, ...nodes.map(item => formatTreeNode(item, 1, parent)));
}

export function setActiveNode(node: ITreeNode, tree: ITreeNode[]) {
  tree.forEach((item) => {
    item.active = item.id === node.id && item.type === node.type;
    if (item.child?.length) {
      setActiveNode(node, item.child);
    }
  });
}
