<template>
  <span @click.stop="handleShowFilter($event)">
    <i :class="[
      'nodeman-icon nc-filter-fill',
      { 'active': active }
    ]"></i>
  </span>
</template>
<script lang="ts">
import { Component, Vue, Prop, Emit, Watch } from 'vue-property-decorator';
import TableFilter from './table-filter.vue';
import i18n from '@/setup';

@Component({ name: 'filter-funnel' })
export default class FilterFunnel extends Vue {
  @Prop({ default: '' }) private readonly data!: string;

  private tableFilterInstance: TableFilter = new TableFilter({ i18n }).$mount();
  private instance: any = null;
  private innerData = this.data;

  public get active() {
    return !!this.innerData || (this.instance && this.instance.state.isShown);
  }

  @Watch('data', { deep: true, immediate: true })
  private handleDataChange() {
    this.handleResetData();
  }

  private created() {
    this.tableFilterInstance.ruleName = this.innerData;
    this.tableFilterInstance.$on('confirm', this.handleConfirm);
    this.tableFilterInstance.$on('reset', this.handleReset);
  }

  public handleShowFilter(e: Event) {
    if (!this.instance && e.target) {
      this.instance = this.$bkPopover(e.target, {
        content: this.tableFilterInstance.$el,
        placement: 'bottom',
        trigger: 'manual',
        theme: 'light filter-header',
        sticky: true,
        duration: [275, 0],
        interactive: true,
        boundary: 'window',
        onHidden: () => {
          this.handleResetData();
        },
      });
    }
    this.instance && this.instance.show(100);
  }

  @Emit('reset')
  public handleReset(name: string) {
    this.handleSetData(name);
    return name;
  }

  @Emit('confirm')
  public handleConfirm(name: string) {
    this.handleSetData(name);
    return name;
  }

  public handleSetData(name: string) {
    this.innerData = name;
    this.instance && this.instance.hide();
  }

  public handleResetData() {
    this.innerData = this.data;
    this.tableFilterInstance.ruleName = this.innerData;
  }
}
</script>
<style lang="postcss" scoped>
.nc-filter-fill {
  color: #c4c6cc;
  cursor: pointer;
  &.active {
    color: #3a84ff;
  }
}
</style>
