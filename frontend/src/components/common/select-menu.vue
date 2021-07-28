<template>
  <!-- 默认列表 -->
  <div class="select-menu-wrap" v-show="false">
    <div class="select-menu-content" ref="content">
      <ul class="default-content-list"
          :style="{ minWidth: `${minWidth}px` }"
          v-if="list.length">
        <auth-component
          v-for="(item, index) in list"
          :key="index"
          :class="['list-item', { 'is-disabled': item.disabled }]"
          tag="li"
          :authorized="item.authorized === undefind || item.authorized"
          :apply-info="[authInfo]"
          @mousedown="handleMousedown(item, index)">
          {{item.name}}
        </auth-component>
      </ul>
      <div v-if="!list.length && !needDelete" class="no-list">{{$t('暂无可选项')}}{{ list.length }}</div>
      <div class="del-btn" @mousedown="handleDel" v-show="needDelete">{{$t('删除')}}</div>
    </div>
  </div>
</template>
<script lang="ts">
import { TranslateResult } from 'vue-i18n';
import { Vue, Component, Prop, Emit, Watch, Ref } from 'vue-property-decorator';

export interface IListItem {
  id: string | number
  name: string | number | TranslateResult,
  disabled?: boolean
  authorized?: boolean
}

@Component({ name: 'select-menu' })
export default class SelectMenu extends Vue {
  // 触发目标
  @Prop({ default: null, type: HTMLElement }) private readonly target!: HTMLElement;
  // 选择列表
  @Prop({ default: null, type: Object }) private readonly content!: HTMLElement;
  @Prop({ default: false, type: Boolean }) private readonly show!: boolean;
  @Prop({ default: false, type: Boolean }) private readonly needDelete!: boolean;
  @Prop({ default: 78, type: Number }) private readonly minWidth!: number;
  @Prop({ default: () => ({}), type: Object }) private readonly authInfo!: Dictionary;

  // 默认列表数据
  @Prop({ default: () => [], type: Array }) private readonly list!: IListItem[];

  @Ref('content') private readonly defaultContent!: HTMLElement;

  private popoverInstance: any = null;

  @Watch('show', { immediate: true })
  private showChange(v: boolean) {
    if (v) {
      this.$nextTick(() => {
        this.initPopover();
      });
    } else {
      this.hiddenPopover();
    }
  }

  @Emit('on-hidden')
  private handleHidden() {
    this.hiddenPopover();
    return 'hidden';
  }

  private initPopover() {
    if (!this.popoverInstance) {
      this.popoverInstance = this.$bkPopover(this.target, {
        content: this.defaultContent,
        trigger: 'manual',
        theme: 'light menu',
        interactive: true,
        arrow: false,
        placement: 'bottom-start',
        maxWidth: 300,
        delay: 100,
        offset: -1,
        distance: 12,
        followCursor: false,
        flip: true,
        // duration: [275, 250],
        animation: 'slide-toggle',
        boundary: 'window',
        zIndex: 2000,
        onHidden: () => {
          this.handleHidden();
        },
      });
    }
    this.popoverInstance && this.popoverInstance.show();
  }

  private hiddenPopover() {
    this.popoverInstance && this.popoverInstance.hide();
    this.popoverInstance && this.popoverInstance.destroy();
    this.popoverInstance = null;
  }
  private handleMousedown(item: Dictionary, i: string | number) {
    if (!item.disabled) {
      this.handleSelect(item.id, i);
    }
  }

  @Emit('on-select')
  private handleSelect(v: string | number, i: string | number) {
    this.hiddenPopover();
    return { id: v, index: i };
  }

  @Emit('on-delete')
  private handleDel() {
    this.hiddenPopover();
    return 'delete';
  }
}
</script>
<style lang="scss" scoped>

.select-menu-content {
  display: flex;
  flex-direction: column;
  border: 1px solid #dcdee5;
  border-radius: 2px;
  background-color: #fff;
  //   min-width: 98px;
  .default-content-list {
    display: flex;
    flex-direction: column;
    padding: 6px 0;
    box-sizing: border-box;
    max-height: 210px;
    overflow: auto;
    .list-item {
      flex: 0 0 32px;
      display: flex;
      align-items: center;
      padding: 0 15px;
      color: #63656e;
      font-size: 12px;
      &:hover {
        background-color: #e1ecff;
        color: #3a84ff;
        cursor: pointer;
      }
      &.is-disabled {
        color: #dcdee5;
        background-color: #fff;
        cursor: not-allowed;
      }
    }
  }
  .no-list {
    height: 32px;
    line-height: 32px;
    padding: 0 15px;
  }
  .del-btn {
    flex: 0 0 32px;
    // border-top: 1px solid #dcdee5;
    display: flex;
    align-items: center;
    background-color: #fafbfd;
    padding: 0 15px;
    cursor: pointer;
    &-icon {
      margin-right: 4px;
    }
  }
}
</style>
