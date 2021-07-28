<template>
  <span :class="['sort-wrapper', sort.active]">
    <i class="sort-caret ascending" @click.stop="sortAsc"></i>
    <i class="sort-caret descending" @click.stop="sortDesc"></i>
  </span>
</template>
<script lang="ts">
import { Vue, Component, Emit } from 'vue-property-decorator';

@Component({ name: 'sort-caret' })
export default class SortCaret extends Vue {
  private sort = {
    active: 'normal',
    list: [
      {
        id: 'asc',
        name: 'asc',
        next: 'desc',
      },
      {
        id: 'desc',
        name: 'desc',
        next: 'normal',
      },
      {
        id: 'normal',
        name: 'normal',
        next: 'asc',
      },
    ],
  };
  @Emit('sort-change')
  public changeSort() {
    const item = this.sort.list.find(item => item.id === this.sort.active);
    if (!item) return this.sort.active;
    this.sort.active = item.next;
    return this.sort.active;
  }
  @Emit('sort-change')
  public sortAsc() {
    this.sort.active = 'asc';
    return this.sort.active;
  }
  @Emit('sort-change')
  public sortDesc() {
    this.sort.active = 'desc';
    return this.sort.active;
  }
}
</script>
<style lang="postcss" scoped>
.sort-wrapper {
  position: relative;
  height: 20px;
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  &.asc .sort-caret.ascending {
    border-bottom-color: #63656e;
  }
  &.desc .sort-caret.descending {
    border-top-color: #63656e;
  }
  .sort-caret {
    width: 0;
    height: 0;
    border: 5px solid transparent;
    position: absolute;
    &.ascending {
      border-bottom-color: #c4c6cc;
      top: -1px;
    }
    &.descending {
      border-top-color: #c4c6cc;
      bottom: -1px;
    }
  }
}
</style>
