<template>
  <bk-form-item :label="$t('安装方式')" :required="required" v-test.common="'installMethod'">
    <div class="bk-button-group mothod-switch">
      <bk-button
        :class="{ 'is-selected': !isManual }"
        v-bk-tooltips="{
          delay: [300, 0],
          content: $t('远程安装提示'),
          theme: 'light'
        }"
        @click="installMethodHandle(false)">
        <span class="text-underline">{{ $t('远程安装') }}</span>
      </bk-button>
      <bk-button
        :class="{ 'is-selected': isManual }"
        v-bk-tooltips="{
          delay: [300, 0],
          content: $t('手动安装提示'),
          theme: 'light',
          width: 205
        }"
        @click="installMethodHandle(true)">
        <span class="text-underline">{{ $t('手动安装') }}</span>
      </bk-button>
    </div>
  </bk-form-item>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';

@Component({ name: 'install-method' })

export default class InstallMethod extends Vue {
  @Prop({ type: Boolean, default: false }) private readonly isManual!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly required!: boolean;

  @Emit('change')
  public handleChange() {
    return !this.isManual;
  }
  public installMethodHandle(isManual: boolean) {
    if (isManual !== this.isManual) {
      this.handleChange();
    }
  }
}
</script>
<style lang="postcss" scoped>
.mothod-switch {
  display: flex;
  width: 480px;
  .bk-button {
    flex: 1;
  }
  .is-selected .text-underline {
    border-bottom: 1px dashed #a3c5fd;
  }
}
</style>
