<template>
  <div class="right-panel" :class="{ 'need-border': needBorder }">
    <div @click="handleTitleClick"
         class="right-panel-title"
         :class="{ 'align-center': alignCenter, 'is-collapse': isEndCollapse }"
         :style="{ 'backgroundColor': titleBgColor }">
      <slot name="panel">
        <slot name="pre-panel"></slot>
        <div class="panel-sub">
          <i class="bk-icon title-icon"
             :style="[iconStyle, { 'color': collapseColor }]"
             :class="[collapse ? 'icon-down-shape' : 'icon-right-shape']">
          </i>
        </div>
        <div class="title-desc">
          <slot name="title">
            已选择<span class="title-desc-num">{{title.num}}</span>个{{title.type || '主机'}}
          </slot>
        </div>
      </slot>
    </div>
    <transition :css="false"
                @before-enter="beforeEnter" @enter="enter" @after-enter="afterEnter"
                @before-leave="beforeLeave" @leave="leave" @after-leave="afterLeave" @leave-cancelled="afterLeave">
      <div class="right-panel-content" v-show="collapse">
        <slot>

        </slot>
      </div>
    </transition>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit, Model } from 'vue-property-decorator';

@Component({ name: 'right-panel' })

export default class RightPanel extends Vue {
  @Model('change', { type: Boolean, default: false }) private collapse!: boolean;
  @Prop({ type: Boolean, default: true }) private readonly alignCenter!: boolean;
  @Prop({ type: Object, default: () => ({
    num: 0,
    type: window.i18n.t('主机') }),
  }) private readonly title!: { nun: number, type: string };
  @Prop({ type: String, default: '#63656e' }) private collapseColor!: string;
  @Prop({ type: String, default: '#fafbfd' }) private titleBgColor!: string;
  @Prop({ type: String, default: '' }) private type!: string;
  @Prop({ type: Boolean, default: false }) private readonly needBorder!: boolean;
  @Prop({ type: [String, Object], default: '' }) private iconStyle!: string | { [key: string]: string };

  private isEndCollapse = this.collapse;

  public beforeEnter(el: HTMLElement) {
    el.classList.add('collapse-transition');
    el.style.height = '0';
  }
  public enter(el: HTMLElement) {
    el.dataset.oldOverflow = el.style.overflow;
    if (el.scrollHeight !== 0) {
      el.style.height = `${el.scrollHeight}px`;
    } else {
      el.style.height = '';
    }
    this.$nextTick().then(() => {
      this.isEndCollapse = this.collapse;
    });
    el.style.overflow = 'hidden';
    setTimeout(() => {
      el.style.height = '';
      el.style.overflow = el.dataset.oldOverflow || '';
    }, 300);
  }
  public afterEnter(el: HTMLElement) {
    el.classList.remove('collapse-transition');
  }
  public beforeLeave(el: HTMLElement) {
    el.dataset.oldOverflow = el.style.overflow;
    el.style.height = `${el.scrollHeight}px`;
    el.style.overflow = 'hidden';
  }
  public leave(el: HTMLElement) {
    if (el.scrollHeight !== 0) {
      el.classList.add('collapse-transition');
      el.style.height = '';
    }
    setTimeout(() => {
      this.isEndCollapse = this.collapse;
    }, 300);
  }
  public afterLeave(el: HTMLElement) {
    el.classList.remove('collapse-transition');
    setTimeout(() => {
      el.style.height = '';
      el.style.overflow = el.dataset.oldOverflow || '';
    }, 300);
  }
  public handleTitleClick() {
    this.handleUpdate();
    this.handleChange();
  }
  @Emit('update:collapse')
  public handleUpdate() {
    return !this.collapse;
  }
  @Emit('change')
  public handleChange() {
    return { value: !this.collapse, type: this.type };
  }
}
</script>
<style lang="postcss" scoped>
  .right-panel {
    &.need-border {
      border: 1px solid #dcdee5;
      border-radius: 2px;
    }
    .right-panel-title {
      display: flex;
      background: #fafbfd;
      color: #63656e;
      font-weight: bold;
      padding: 0 16px;
      cursor: pointer;
      &.is-collapse {
        border-bottom: 1px solid #dcdee5;
      }
      .panel-sub {
        padding: 14px 5px 0 0;
      }
      .title-icon {
        font-size: 16px;
        &:hover {
          cursor: pointer;
        }
      }
      .title-desc {
        color: #979ba5;
        &-num {
          color: #3a84ff;
          margin: 0 3px;
        }
      }
      &.align-center {
        height: 40px;
        align-items: center;
        &.is-collapse {
          height: 41px;
        }
        .panel-sub {
          padding: 0 5px 0 0;
        }
      }
    }
    .right-panel-content {
      /deep/ .bk-table {
        border: 0;
        .bk-table-header {
          th {
            background: #fff;
          }
        }
        &::after {
          width: 0;
        }
      }
    }
    .collapse-transition {
      transition: .3s height ease-in-out;
    }
  }
</style>
