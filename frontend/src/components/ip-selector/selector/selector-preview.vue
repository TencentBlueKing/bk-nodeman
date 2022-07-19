<template>
  <div class="selector-preview"
       :style="{ width: isNaN(preWidth) ? preWidth : `${preWidth}px` }"
       v-show="isNaN(preWidth) || preWidth > 0">
    <div class="selector-preview-title">
      <slot name="title">{{ $t('策略部署范围') }}</slot>
    </div>
    <div class="selector-preview-content">
      <template v-if="!isDataEmpty">
        <bk-collapse v-model="activeName">
          <bk-collapse-item
            v-for="item in data"
            :key="item.id"
            :name="item.id"
            hide-arrow
            v-show="item.data && item.data.length">
            <template #default>
              <div class="collapse-title">
                <span class="collapse-title-left">
                  <i :class="['bk-icon icon-angle-right', { expand: activeName.includes(item.id) }]"></i>
                  <slot name="collapse-title" v-bind="{ item }">
                    <i18n :path="isTopoActive ? '节点个数' : 'IP个数'">
                      <span class="num">{{ item.data.length }}</span>
                    </i18n>
                  </slot>
                </span>
                <span class="collapse-title-right" @click.stop="handleShowMenu($event, item)">
                  <i class="bk-icon icon-more"></i>
                </span>
              </div>
            </template>
            <template #content>
              <slot name="collapse-content" v-bind="{ item }">
                <ul class="collapse-content">
                  <li v-for="(child, index) in item.data"
                      :key="index"
                      class="collapse-content-item"
                      @mouseenter="hoverChild = child"
                      @mouseleave="hoverChild = null">
                    <span class="left" :title="child[item.dataNameKey] || child.name || '--'">
                      {{ child[item.dataNameKey] || child.name || '--' }}
                    </span>
                    <span class="right"
                          v-show="hoverChild === child"
                          @click="removeNode(child, item)">
                      <i class="bk-icon icon-close-line"></i>
                    </span>
                  </li>
                </ul>
              </slot>
            </template>
          </bk-collapse-item>
        </bk-collapse>
      </template>
      <template v-else>
        <bk-exception class="empty" type="empty" scene="part">
          <span class="empty-text">{{ $t('请在左侧勾选IP或者节点') }}</span>
        </bk-exception>
      </template>
    </div>
    <div class="drag" @mousedown="handleMouseDown"></div>
    <div v-show="false">
      <Menu ref="menuRef" theme="primary" :list="moreOperateList" @click="handleMenuClick">
        <div class="operate-item" slot-scope="{ item }">
          <span class="operate-item-label">{{ item.label }}</span>
          <p class="operate-item-desc text-ellipsis" :title="$t('已部署插件的主机将被停止')">
            <i class="nodeman-icon nc-install"></i>
            <span class="ml5">{{ $t('已部署插件的主机将被停止') }}</span>
          </p>
        </div>
      </Menu>
    </div>
  </div>
</template>
<script lang="ts">
import { Component, Vue, Prop, Emit, Watch, Ref } from 'vue-property-decorator';
import { IPreviewData, IMenu, IPerateFunc } from '../types/selector-type';
import { Debounce } from '../common/util';
import Menu from '../components/menu.vue';

// 预览区域
@Component({ name: 'selector-preview', components: { Menu } })
export default class SelectorPreview extends Vue {
  @Prop({ default: 280, type: [Number, String] }) private readonly width!: number | string;
  @Prop({ default: () => [100, 600], type: Array }) private readonly range!: number[];
  @Prop({ default: () => [], type: Array }) private readonly data!: any[];
  @Prop({ default: () => [], type: [Array, Function] }) private readonly operateList!: IMenu[] | IPerateFunc;
  @Prop({ default: () => [], type: Array }) private readonly defaultActiveName!: string[];

  @Ref('menuRef') private readonly menuRef!: any;

  private preWidth = this.width;
  private activeName = this.defaultActiveName;
  private hoverChild = null;
  private popoverInstance: any = null;
  private moreOperateList: IMenu[] = [];
  private previewItem: IPreviewData = null;

  private get isDataEmpty() {
    return !this.data.length || this.data.every(item => !item.data.length);
  }
  private get isTopoActive() {
    return this.data.some(item => item.id === 'TOPO');
  }

  @Watch('width')
  private handleChange(width: number) {
    this.preWidth = width;
  }

  @Debounce(300)
  @Emit('update:width')
  private handleWidthChange() {
    return this.preWidth;
  }

  @Emit('menu-click')
  private handleMenuItemClick(menu: IMenu, item: IPreviewData) {
    return {
      menu,
      item,
    };
  }

  @Emit('remove-node')
  private removeNode(child: any, item: IPreviewData) {
    const index = item.data.indexOf(child);
    this.hoverChild = index > -1 && item.data[index + 1] ? item.data[index + 1] : null;
    return {
      child,
      item,
    };
  }

  private handleMenuClick(menu: IMenu) {
    this.popoverInstance && this.popoverInstance.hide();
    this.handleMenuItemClick(menu, this.previewItem);
  }

  private async handleShowMenu(event: Event, item: IPreviewData) {
    if (!event.target) return;

    const list = typeof this.operateList === 'function'
      ? await this.operateList(item)
      : this.operateList;

    if (!list || !list.length) return;

    this.moreOperateList = list;

    this.previewItem = item;

    this.popoverInstance = this.$bkPopover(event.target, {
      content: this.menuRef.$el,
      trigger: 'manual',
      arrow: false,
      theme: 'light ip-selector',
      maxWidth: 280,
      offset: '0, 5',
      sticky: true,
      duration: [275, 0],
      interactive: true,
      boundary: 'window',
      placement: 'bottom-end',
      onHidden: () => {
        this.popoverInstance && this.popoverInstance.destroy();
        this.popoverInstance = null;
      },
    });
    this.popoverInstance.show();
  }

  private handleMouseDown(e: MouseEvent) {
    const node = e.target as HTMLElement;
    const parentNode = node.parentNode as HTMLElement;

    if (!parentNode) return;

    const nodeRect = node.getBoundingClientRect();
    const rect = parentNode.getBoundingClientRect();
    document.onselectstart = function () {
      return false;
    };
    document.ondragstart = function () {
      return false;
    };
    const handleMouseMove = (event: MouseEvent) => {
      const [min, max] = this.range;
      const newWidth = rect.right - event.clientX + nodeRect.width;
      if (newWidth < min) {
        this.preWidth = 0;
      } else {
        this.preWidth = Math.min(newWidth, max);
      }
      this.handleWidthChange();
    };
    const handleMouseUp = () => {
      document.body.style.cursor = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.onselectstart = null;
      document.ondragstart = null;
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }
}
</script>
<style>
.ip-selector-theme {
  /* stylelint-disable-next-line declaration-no-important */
  padding: 0 !important;
}
</style>
<style lang="scss" scoped>
>>> .bk-collapse-item {
  margin-bottom: 10px;
  .bk-collapse-item-header {
    padding: 0;
    height: 24px;
    line-height: 24px;
    &:hover {
      color: #63656e;
    }
  }
}
.operate-item {
  line-height: 23px;
  &-name {
    font-size: 14px;
  }
  &-desc {
    font-size: 12px;
    color: #979ba5;
  }
  &:hover {
    .operate-item-desc {
      color: #699df4;
    }
  }
}
.selector-preview {
  border: 1px solid #dcdee5;
  background: #f5f6fa;
  position: relative;
  height: 100%;
  &-title {
    color: #313238;
    font-size: 14px;
    line-height: 22px;
    padding: 10px 24px;
  }
  &-content {
    height: calc(100% - 42px);
    overflow: auto;
    .empty {
      margin-top: 30%;
      &-text {
        color: #979ba5;
      }
    }
    .collapse-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 24px 0 18px;
      &-left {
        display: flex;
        align-items: center;
        font-size: 12px;
        .num {
          color: #3a84ff;
          font-weight: 700;
          padding: 0 2px;
        }
      }
      &-right {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 2px;
        &:hover {
          background: #e1ecff;
          color: #3a84ff;
        }
        i {
          font-size: 18px;
          outline: 0;
        }
      }
    }
    .collapse-content {
      padding: 0 14px;
      margin-top: 6px;
      &-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 32px;
        line-height: 32px;
        background: #fff;
        padding: 0 12px;
        border-radius: 2px;
        box-shadow: 0px 1px 2px 0px rgba(0,0,0,.06);
        margin-bottom: 2px;
        .left {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          word-break: break-all;
        }
        .right {
          cursor: pointer;
          color: #3a84ff;
          i {
            font-weight: 700;
          }
        }
      }
    }
    .icon-angle-right {
      font-size: 24px;
      transition: transform .2s ease-in-out;
      &.expand {
        transform: rotate(90deg);
      }
    }
  }
}
.drag {
  position: absolute;
  left: 0px;
  top: calc(50% - 10px);
  width: 6px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-items: center;
  outline: 0;
  &::after {
    content: " ";
    height: 18px;
    width: 0;
    border-left: 2px dotted #c4c6cc;
    position: absolute;
    left: 2px;
  }
  &:hover {
    cursor: col-resize;
  }
}
</style>
