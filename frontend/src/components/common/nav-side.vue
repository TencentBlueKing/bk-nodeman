<template>
  <section class="nodeman-side">
    <!--左侧导航-->
    <bk-navigation-menu
      :default-active="currentActive"
      v-test.nav="'side'"
      @select="handleSelect">
      <bk-navigation-menu-item
        v-for="item in list"
        :has-child="item.children && !!item.children.length"
        :group="item.group"
        :key="item.title"
        :icon="item.icon"
        :disabled="item.disabled"
        :id="item.name">
        <span>{{ $t(item.title) }}</span>
      </bk-navigation-menu-item>
    </bk-navigation-menu>
  </section>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';
import { ISubNavConfig } from '@/types';

const EVENT_SELECT_SUB_MENU = 'select-change';

@Component({ name: 'NavSide' })
export default class NavSide extends Vue {
  @Prop({ type: String, default: '' }) private readonly currentActive!: string;
  @Prop({ type: Array, default: false }) private readonly list!: ISubNavConfig[];

  @Emit(EVENT_SELECT_SUB_MENU)
  public handleSelectEmit(name: string) {
    return name;
  }
  private handleSelect(name: string) {
    if (this.$route.name === name) return;
    this.$router.push({
      name,
    });
    this.handleSelectEmit(name);
  }
}
</script>

<style lang="postcss" scoped>
.nodeman-side {
  color: #fff;
  >>> span.bk-icon {
    /* stylelint-disable-next-line declaration-no-important */
    font-family: "nodeman" !important;
  }
}
</style>
