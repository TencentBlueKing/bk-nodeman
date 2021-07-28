<template>
  <div class="footer">
    <div class="footer-left">
      <slot></slot>
    </div>
    <div class="footer-right" v-if="footerButton">
      <bk-button
        theme="primary"
        class="btn"
        @click="handleConfirm">
        {{ $t('确定') }}
      </bk-button>
      <bk-button class="ml5 btn" @click="handleCancel">{{ $t('取消') }}</bk-button>
    </div>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Emit, Prop } from 'vue-property-decorator';

@Component({ name: 'select-footer' })
export default class SelectFooter extends Vue {
  @Prop({ default: true }) private readonly footerButton!: boolean;
  @Emit('confirm')
  public handleConfirm() {}
  @Emit('cancel')
  public handleCancel() {}
}
</script>
<style lang="postcss" scoped>
.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  background: #fafbfd;
  border-top: 1px solid #dcdee5;
  border-radius: 0px 0px 2px 2px;
  height: 50px;
  line-height: 50px;
  .btn {
    min-width: 86px;
  }
}
</style>
