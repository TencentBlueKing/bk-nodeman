<template>
  <ul :class="`menu ${ theme }`">
    <li v-for="(item, index) in list"
        :key="index"
        class="menu-item"
        :style="{ 'text-align': align }"
        :disabled="item.disabled"
        v-show="!item.hidden"
        @click="!item.disabled && handleMenuClick(item)">
      <slot :item="item">
        {{ item.label }}
      </slot>
    </li>
  </ul>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';
import { IMenu } from '../types/selector-type';

@Component({ name: 'menu-list' })
export default class Menu extends Vue {
  @Prop({ default: () => [], type: Array }) private readonly list!: IMenu[];
  @Prop({ default: 'left', type: String }) private readonly align!: string;
  @Prop({ default: '', type: String }) private readonly theme!: string;

  @Emit('click')
  private handleMenuClick(item: IMenu) {
    return item;
  }
}
</script>
<style lang="scss" scoped>
.menu {
  font-size: 12px;
  padding: 6px 0;
  min-width: 84px;
  background: #fff;
  &-item {
    // height: 32px;
    line-height: 32px;
    padding: 0 10px;
    cursor: pointer;
    white-space: nowrap;
    &:hover {
      background: #f5f6fa;
      color: #3a84ff;
    }
  }
  &-item[disabled] {
    color: #c4c6cc;
    cursor: not-allowed;
  }
  &.primary .menu-item:hover {
    background: #e1ecff;
  }
}
</style>
