<template>
  <section>
    <div class="filter-header" :class="{ 'default': filterList.length === 0 }" @click.stop="handleShow($event)">
      {{ name }}
      <i
        class="header-icon nodeman-icon nc-filter-fill"
        :class="{ 'is-selected': isSelected }"
        v-if="filterList.length">
      </i>
    </div>
    <!--筛选面板-->
    <div v-show="false">
      <div class="label-menu-wrapper" ref="labelMenu" :style="{ width: isNaN(width) ? width : `${width}px` }">
        <bk-input
          class="search"
          :placeholder="$t('请输入关键字')"
          clearable
          left-icon="bk-icon icon-search"
          v-model="searchValue"
          v-if="showSearch">
        </bk-input>
        <ul class="label-menu-list" v-if="filterList.length">
          <li v-if="checkAll && currentList.length" class="item" @click="handleSelectAll">
            <bk-checkbox class="check-box" :checked="isCheckAllCompted" :value="isCheckAll"></bk-checkbox>
            <span class="item-name">{{ $t('全选') }}</span>
          </li>
          <li
            class="item"
            v-for="(item, index) in currentList"
            :title="item.name"
            :key="index"
            @click="handleSelectLabel(item)">
            <bk-checkbox class="check-box" :value="item.checked"></bk-checkbox>
            <span class="item-name">{{item.name}}</span>
          </li>
          <li class="item-empty" v-show="!currentList.length">
            {{ $t('无匹配数据') }}
          </li>
        </ul>
        <div class="footer" :style="{ 'justify-content': footerAlign }" v-if="filterList.length">
          <bk-button text @click="handleConfirm" ext-cls="footer-btn mr20">{{ $t('确定') }}</bk-button>
          <bk-button text @click="handleResetSelected" ext-cls="footer-btn">{{ $t('重置') }}</bk-button>
        </div>
      </div>
    </div>
  </section>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit, Watch, Ref } from 'vue-property-decorator';
import { ISearchChild } from '@/types';
import { isEmpty } from '@/common/util';

@Component({ name: 'filter-header' })

export default class FilterHeader extends Vue {
  @Ref('labelMenu') private readonly refLabelMenu: any;

  @Prop({ type: String, default: '' }) private readonly name!: string;
  @Prop({ type: Array, default: () => ([]) }) private readonly filterList!: ISearchChild[];
  @Prop({ type: String, default: '' }) private readonly property!: string;
  @Prop({ type: Boolean, default: false }) private readonly checkAll!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly showSearch!: boolean;
  @Prop({ type: [Number, String], default: 'auto' }) private readonly width!: string | number;
  @Prop({
    type: String,
    default: 'center',
    validator(v) {
      return ['left', 'right', 'center'].includes(v);
    },
  }) private readonly align!: string;

  private instance: any = null;
  private list: ISearchChild[] = JSON.parse(JSON.stringify(this.filterList));
  private selectIds: Array<number|string> = [];
  private searchValue = '';
  private isCheckAll = false;

  private get isSelected() {
    return this.list.some(item => item.checked);
  }
  private get footerAlign(): string {
    switch (this.align) {
      case 'center':
        return 'space-between';
      case 'left':
        return 'flex-start';
      case 'right':
        return 'flex-end';
      default:
        return 'space-between';
    }
  }
  private get currentList(): ISearchChild[] {
    return isEmpty(this.searchValue) ? this.list
      : this.list.filter(item => item.name && ~item.name.toString().toLocaleLowerCase()
        .indexOf(this.searchValue.toLocaleLowerCase()));
  }
  private get isCheckAllCompted(): boolean {
    return !this.checkAll || this.currentList.every((item: ISearchChild) => item.checked);
  }

  @Watch('filterList', { deep: true })
  private filterListChange(val: ISearchChild[]) {
    this.list = JSON.parse(JSON.stringify(val));
    this.selectIds = this.list.filter(item => item.checked).map(item => item.id);
  }

  private beforeDestroy() {
    this.instance && this.instance.destroy();
    this.instance = null;
  }

  public handleShow(e: Event) {
    if (!this.filterList.length) return;
    // const target = e.target.tagName === 'SPAN' ? e.target : e.target.parentNode
    if (!this.instance) {
      this.instance = this.$bkPopover(e.target as EventTarget, {
        content: this.refLabelMenu,
        trigger: 'click',
        arrow: false,
        placement: 'bottom',
        theme: 'light filter-header',
        maxWidth: 520,
        offset: '0, 0',
        sticky: true,
        duration: [275, 0],
        interactive: true,
        onHidden: () => {
          this.list.forEach((item) => {
            item.checked = this.selectIds.includes(item.id);
          });
          this.instance && this.instance.destroy();
          this.instance = null;
        },
      });
    }
    this.instance && this.instance.show(100);
  }
  public handleSelectLabel(item: ISearchChild) {
    item.checked = !item.checked;
  }
  public handleSelectAll() {
    this.isCheckAll = this.isCheckAllCompted ? false : !this.isCheckAll;
    if (this.isCheckAll) {
      const selected = this.currentList.map(item => item.id);
      this.list.forEach((item) => {
        item.checked = selected.includes(item.id);
      });
    } else {
      this.list.forEach((item) => {
        item.checked = false;
      });
    }
  }
  public handleConfirm() {
    // this.$emit('update:filterList', this.list)
    this.selectIds = this.list.filter(item => item.checked).map(item => item.id);
    if (this.selectIds.length) {
      this.handleConfirmEmit();
    } else {
      this.handleResetEmit();
    }
    this.instance && this.instance.hide(100);
  }
  @Emit('confirm')
  public handleConfirmEmit() {
    return {
      prop: this.property,
      list: this.list,
    };
  }
  @Emit('reset')
  public handleResetEmit() {
    return this.property;
  }
  @Emit('reset')
  public handleResetSelected() {
    this.selectIds = [];
    this.list.forEach((item) => {
      item.checked = false;
    });
    this.instance && this.instance.hide(100);
    return this.property;
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

.filter-header {
  cursor: pointer;
  outline: 0;
  &.default {
    cursor: default;
  }
  .header-icon {
    position: relative;
    font-size: 13px;
    color: #c4c6cc;
    outline: 0;
  }
  .is-selected {
    color: #3a84ff;
  }
}
.label-menu-wrapper {
  min-width: 100px;
  .search {
    >>> .bk-input-text {
      padding: 0 5px;
      input {
        border: 0;
        border-bottom: 1px solid #f0f1f5;
      }
    }
    >>> .icon-search {
      color: #979ba5;
    }
  }
  .label-menu-list {
    max-height: 260px;
    overflow: auto;
    padding: 6px 0;
    .item {
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      padding: 0 10px;
      height: 32px;

      @mixin layout-flex row, center;
      .check-box {
        overflow: unset;
      }
      &:hover {
        background: #e1ecff;
        color: #3a84ff;
      }
      &-name {
        margin-left: 6px;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
      }
    }
    .item-empty {
      font-size: 12px;
      text-align: center;
      color: #c4c6cc;
      line-height: 24px;
    }
  }
  .footer {
    padding: 0 15px;
    height: 30px;
    border-top: 2px solid #f0f1f5;

    @mixin layout-flex row, center, space-between;
    &-btn {
      font-size: 12px;
    }
  }
}
</style>
