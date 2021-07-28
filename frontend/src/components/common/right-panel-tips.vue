<template>
  <bk-sideslider
    transfer
    quick-close
    :is-show="show"
    :width="1200"
    :title="title"
    :before-close="handleToggleTips">
    <StrategyTemplate
      v-if="show"
      slot="content"
      class="operation-tips"
      :host-type="hostType"
      :host-list="hostList">
    </StrategyTemplate>
  </bk-sideslider>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit, Model } from 'vue-property-decorator';
import StrategyTemplate from '@/components/common/strategy-template.vue';

@Component({
  name: 'panel-tips',
  components: {
    StrategyTemplate,
  },
})
export default class PanelTips extends Vue {
  @Model('update') private readonly show!: boolean;

  @Prop({ type: String, default: window.i18n.t('安装策略') }) private readonly title!: string;
  @Prop({ type: String, default: 'Agent' }) private readonly hostType!: string;
  @Prop({ type: Array, default: () => ([]) }) private readonly hostList!: any[];

  @Emit('update')
  public handleToggleTips() {
    return false;
  }
}
</script>
<style lang="postcss" scoped>
    @import "@/css/mixins/nodeman.css";

    .operation-tips {
      padding: 20px 30px;
      background: #fff;
    }
</style>
