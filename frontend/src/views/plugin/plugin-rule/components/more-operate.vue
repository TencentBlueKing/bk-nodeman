<template>
  <ul class="menu">
    <li v-for="item in data"
        :key="item.id"
        :class="['menu-item', { disabled: item.disabled }]"
        @click="handleClick(item)">
      <slot v-bind="{ item }">
        {{ item.name }}
      </slot>
    </li>
  </ul>
</template>
<script lang="ts">
import { Vue, Component, Prop, Watch, Emit } from 'vue-property-decorator';
import { IMenu } from '@/types/plugin/plugin-type';

@Component({ name: 'more-operate' })
export default class MoreOperate extends Vue {
  @Prop({ default: () => [], type: Array }) private readonly list!: IMenu[];

  public data: IMenu[] = [];

  @Watch('list', { immediate: true, deep: true })
  private handleListChange() {
    this.setData();
  }

  public setData() {
    this.data = JSON.parse(JSON.stringify(this.list));
  }
  @Emit('click')
  private handleClick(item: IMenu) {
    return item;
  }
}
</script>
<style lang="postcss" scoped>
.menu {
  min-width: 70px;
  padding: 6px 0;
  font-size: 12px;
  color: #63656e;
  background: #fff;
  &-item[disabled] {
    color: #dcdee5;
    cursor: not-allowed;
    &:hover {
      color: #dcdee5;
    }
  }
  &-item {
    height: 32px;
    line-height: 32px;
    padding: 0 15px;
    cursor: pointer;
    &:hover {
      background: #e5efff;
      color: #3a84ff;
    }
  }
}
</style>
