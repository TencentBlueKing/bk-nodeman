<template>
  <bk-big-tree
    :style="{ 'height': '100%' }"
    :data="nodes"
    selectable
    @select-change="handleSelectChange">
    <template #default="{ data, node }">
      <div class="node-label">
        <span>{{ data.name }}</span>
        <span :class="['num', { 'selected': node.selected }]">
          {{ data.children ? data.children.length : 0 }}
        </span>
      </div>
    </template>
  </bk-big-tree>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';

interface ITreeNode {
  id: string | number
  name: string
  level: string | number
  children: ITreeNode[]
}

@Component({ name: 'static-topo' })
export default class StaticTopo extends Vue {
  @Prop({ default: () => [
    {
      id: '1',
      name: '王者荣耀',
      children: [
        {
          id: '1-1',
          name: '王者荣耀1',
        },
        {
          id: '1-2',
          name: '王者荣耀2',
        },
      ],
    },
    {
      id: '2',
      name: '蓝鲸',
      children: [
        {
          id: '2-1',
          name: '蓝鲸 PaaS 平台',
        },
      ],
    },
  ], type: Array }) private readonly nodes!: ITreeNode;

  @Emit('select-change')
  public handleSelectChange(treeNode: any) {
    return treeNode;
  }
}
</script>
<style lang="postcss" scoped>
.node-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  .num {
    background: #f0f1f5;
    border-radius: 2px;
    height: 18px;
    line-height: 18px;
    padding: 0 5px;
    color: #979ba5;
  }
}
</style>
