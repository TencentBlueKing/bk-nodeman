<template>
  <bk-sideslider
    transfer
    quick-close
    :width="1060"
    :is-show="show"
    :before-close="handleHidden">
    <template #header>{{ ip }}</template>
    <div class="content-box" slot="content" v-bkloading="{ isLoading: loading }">
      <node-detail-table v-if="!loading" :data="detailData" />
    </div>
    <!-- <div slot="content" v-else>
      <bk-exception class="exception-agent" type="500">
        <div class="exception-agent-title">{{ $t('Agent状态异常') }}</div>
        <bk-button text @click="handleGotoAgentList">{{ $t('前往Agent管理查看') }}</bk-button>
      </bk-exception>
    </div> -->
  </bk-sideslider>
</template>
<script lang="ts">
import { Vue, Component, Prop, Model, Emit } from 'vue-property-decorator';
import NodeDetailTable from './node-detail-table.vue';
import { IPluginStatus } from '@/types/plugin/plugin-type';

@Component({
  name: 'node-detail-slider',
  components: {
    NodeDetailTable,
  },
})
export default class PluginRuleTable extends Vue {
  @Prop({ default: '', type: String }) private readonly ip!: string;
  @Prop({ default: '', type: [String, Number] }) private readonly bkHostId!: string;
  @Prop({ default: () => [], type: Array }) private readonly detailData!: IPluginStatus[];
  @Model('update', { default: false }) private readonly show!: boolean;
  @Prop({ default: false, type: Boolean }) private readonly loading!: boolean;
  @Prop({ default: '', type: String }) private readonly status!: string;

  @Emit('update')
  public handleHidden() {
    return false;
  }

  private handleGotoAgentList() {
    this.$router.push({
      name: 'agentStatus',
      params: {
        ipList: [this.ip],
      },
    });
  }
}
</script>
<style lang="postcss" scoped>
  >>>.bk-sideslider-content,
  .content-box {
    height: 100%;
  }
  .exception-agent {
    margin-top: 20%;
    &-title {
      font-size: 20px;
    }
  }
</style>
