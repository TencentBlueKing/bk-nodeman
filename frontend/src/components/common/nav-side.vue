<template>
  <section class="nodeman-side">
    <!--左侧导航-->
    <bk-navigation-menu
      :default-active="currentActive"
      v-test.nav="'side'"
      item-default-color="#63656e"
      item-active-color="#3a84ff"
      item-default-icon-color="#979ba5"
      item-active-icon-color="#3a84ff"
      item-hover-icon-color="#979ba5"
      item-hover-bg-color="#f5f7fa"
      item-active-bg-color="#e1ecff"
      @select="handleSelect">
      <template v-for="item in list">
        <bk-navigation-menu-group
          v-if="item.children && item.children.length"
          :key="item.title"
          :group-name="$t(item.name)">
          <bk-navigation-menu-item
            v-for="child in item.children"
            :key="child.name"
            :id="child.name"
            :disabled="child.disabled"
            :icon="child.icon"
            :has-child="child.children && !!child.children.length"
            :default-active="child.active">
            <span>{{ $t(child.title) }}</span>
            <!-- <div slot="child">
              <bk-navigation-menu-item
                v-for="set in child.children"
                :key="set.name"
                :id="set.name"
                :disabled="set.disabled"
                :href="set.href"
                :default-active="set.active">
                <span>{{ set.name }}</span>
              </bk-navigation-menu-item>
            </div> -->
          </bk-navigation-menu-item>
        </bk-navigation-menu-group>
        <template v-else>
          <bk-navigation-menu-item
            :group="item.group"
            :key="item.title"
            :icon="item.icon"
            :disabled="item.disabled"
            :id="item.name">
            <div class="text-ellipsis" v-bk-overflow-tips>
              <span>{{ $t(item.title) }}</span>
            </div>
          </bk-navigation-menu-item>
        </template>
      </template>
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
