<template>
  <bk-select
    ext-popover-cls="nodeman-strategy-topo"
    :value="value"
    :placeholder="$t('选择部署策略')"
    :loading="loading"
    searchable
    @change="handleChange">
    <bk-option
      v-for="(option, index) in optionsData"
      :key="option.id"
      :id="option.id"
      :name="option.name"
      :style="{ paddingLeft: index === 0 ? '18px' : `${ 24 * option.index + 18 }px` }">
      <div class="topo-name">{{ option.name }}</div>
    </bk-option>
  </bk-select>
</template>
<script lang="ts">
import { Vue, Prop, Component, Model, Watch, Emit } from 'vue-property-decorator';
import { INode } from '@/types/plugin/plugin-type';

@Component({ name: 'strategy-topo' })
export default class StrategyTopo extends Vue {
  @Model('change', { default: '' }) private readonly value!: string | number;
  @Prop({ default: () => [], type: Array }) private readonly list!: INode[];
  @Prop({ default: false, type: Boolean }) private readonly loading!: boolean;

  private optionsData: INode[] = [];

  @Watch('list', { immediate: true })
  private handleListChange() {
    this.optionsData = this.flatList(this.list, []);
  }

  @Emit('change')
  public handleChange() {}

  // 打平数据
  public flatList(list: INode[], initialValue: INode[], index = 0) {
    return list.reduce<INode[]>((pre, next) => {
      pre.push({
        id: next.id,
        name: next.name,
        index,
      });
      if (next.children?.length) {
        const data = this.flatList(next.children, pre, index + 1);
        pre.concat(data);
      }
      return pre;
    }, initialValue);
  }
}
</script>
<style lang="postcss" scoped>
.topo-name {
  height: 32px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  word-break: break-all;
}
</style>
