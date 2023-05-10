<template>
  <div>
    <div
      ref="dropdownDefaultRef"
      :class="isShow ? 'dropdown-active' : ''"
      @click="clickShow"
      v-bk-clickoutside="clickoutside">
      <slot />
    </div>
    <div v-show="false">
      <div ref="dropdownContentRef" class="bk-dropdown-content" @click="contentClick">
        <slot name="content" />
      </div>
    </div>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Prop, Ref } from 'vue-property-decorator';

@Component({
  name: 'table-header',
})
export default class MixinsControlDropdown extends Vue {
  @Prop({ type: String, default: '' }) private readonly extCls!: string;
  @Prop({ type: String, default: 'bottom' }) private readonly placement!: string;
  @Prop({ type: String, default: 'nav-dropdown' }) private readonly theme!: string;
  @Prop({ type: Boolean, default: false }) private readonly arrow!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly disabled!: boolean;
  @Prop({ type: Number, default: '0, 0' }) private readonly offset!: string;

  @Ref('dropdownDefaultRef') protected readonly dropdownDefaultRef!: any;
  @Ref('dropdownContentRef') protected readonly dropdownContentRef!: any;

  private isShow = false;
  // 切换Popover的触发方式, 规避无法切换导致的问题 (setProps函数的替代方案, 低版tippy本无此方法)
  private trigger: 'mouseenter' | 'manual' = 'mouseenter';
  private popoverInstance: any = null;
  private closeTimer: number | null = null;

  private mounted() {
    this.updateInstance();
  }
  private beforeDestroy() {
    this.popoverInstance && this.popoverInstance.destroy();
  }
  public updateInstance() {
    this.popoverInstance = this.$bkPopover(this.dropdownDefaultRef, {
      content: this.dropdownContentRef,
      allowHTML: true,
      trigger: 'mouseenter',
      arrow: this.arrow,
      theme: `light bk-dropdown-popover ${this.theme}`,
      offset: this.offset,
      maxWidth: 274,
      sticky: true,
      duration: [275, 0],
      interactive: true,
      boundary: 'window',
      placement: 'top',
      hideOnClick: 'toggle',
      onHide: () => this.trigger === 'mouseenter',
      onTrigger: () => this.isShow = true,
      onHidden: () => this.isShow = false,
    });
  }
  public clickShow() {
    if (this.popoverInstance) {
      this.trigger = 'manual';
      this.popoverInstance.show();
    }
  }
  public clickoutside() {
    this.setTimer();
  }
  public contentClick() {
    this.clearTimer();
    // 可增加 beforeClose 钩子
    this.setTimer();
  }
  public hide() {
    this.trigger = 'mouseenter';
    this.popoverInstance && this.popoverInstance.hide();
  }
  public setTimer() {
    this.closeTimer = window.setTimeout(this.hide, 50);
  };
  public clearTimer() {
    if (this.closeTimer) {
      window.clearTimeout(this.closeTimer);
      this.closeTimer = null;
    }
  };
}
</script>
<style lang="postcss">
</style>
