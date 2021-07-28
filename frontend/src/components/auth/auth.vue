<template>
  <component
    :class="['auth-box', extCls, { 'auth-box-diabled': !isAuthorized }]"
    :is="tag"
    v-cursor="{
      active: !isAuthorized
    }"
    @click.stop="handleAuthApplication">
    <slot :disabled="!isAuthorized" class="diabled-auth"></slot>
  </component>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { MainStore } from '@/store/index';
// import { bus } from '@/common/bus'
// import { IAuth } from '@/types/index'

@Component({ name: 'auth-component' })

export default class AuthComponent extends Vue {
  @Prop({ type: String, default: 'span' }) private readonly tag!: string;
  // 是否有权限
  @Prop({ type: Boolean, default: false }) private readonly authorized!: boolean;
  @Prop({ type: String, default: '' }) private readonly extCls!: string;
  @Prop({ type: String, default: false }) private readonly autoEmit!: boolean;
  @Prop({ type: Object, required: true }) private readonly applyInfo!: any;

  private get permissionSwitch() {
    return MainStore.permissionSwitch;
  }
  private get isAuthorized() {
    return !this.permissionSwitch || this.authorized;
  }

  private handleAuthApplication() {
    if (!this.isAuthorized) {
      window.bus.$emit('show-permission-modal', {
        trigger: 'click',
        params: { apply_info: this.applyInfo },
      });
    }
    if (this.isAuthorized || this.autoEmit) {
      this.$emit('click', this.isAuthorized);
      this.$emit('mousedown', this.isAuthorized);
    }
  }
}
</script>

<style lang="postcss" scoped>
  .auth-box {
    display: inline-block;
  }
  .auth-box-diabled {
    /* stylelint-disable-next-line declaration-no-important */
    color: #dcdee5!important;
  }
</style>
