<template>
  <section class="cloud-channel">
    <div class="tr fs0">
      <bk-button v-test="'editChannel'" @click="handleEdit">{{ $t('编辑') }}</bk-button>
      <bk-popconfirm
        style="margin-left: 8px;"
        width="280"
        trigger="click"
        :title="$t('确认删除此通道')"
        :content="$t('通过此通道安装的Agent不受影响')"
        :disabled="deleteLoading"
        @confirm="confirmDeleteChannel">
        <bk-button class="delete-btn" v-test="'deleteChannel'" :loading="deleteLoading">{{ $t('删除通道') }}</bk-button>
      </bk-popconfirm>
    </div>
    <ChannelTable class="mt20" :channel="channel"></ChannelTable>

    <Tips class="cloud-channel-tips" theme="warning" v-if="showTips">
      <i class="nodeman-icon nc-remind-fill" slot="tipsIcon"></i>
      <span>{{ $t('该通道的节点尚未进行手动部署请根据指引部署方可使用此通道进行agent安装') }}</span>
    </Tips>

    <section class="deploy-guide">
      <div class="markdown-content">
        <ChannelMdFile class="markdown-body"></ChannelMdFile>
      </div>
    </section>
  </section>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import ChannelTable from './channel-table.vue';
import Tips from '@/components/common/tips.vue';
import { CloudStore } from '@/store';
import ChannelMdFile from './install_channel.md';

@Component({
  components: {
    ChannelTable,
    Tips,
    ChannelMdFile,
  },
})
export default class CloudChannel extends Vue {
  @Prop({ default: () => ({}), type: Object }) private readonly channel!: Dictionary;

  private deleteLoading = false;

  private get showTips() {
    return !this.channel || this.channel.status !== 'running';
  }

  @Emit('channel-edit')
  public handleEdit() {
    return true;
  }
  @Emit('channel-delete')
  public handleDelete() {
    return { channel: this.channel, type: 'delete' };
  }

  public async confirmDeleteChannel() {
    this.deleteLoading = true;
    const { id, bk_cloud_id } = this.channel;
    const res = await CloudStore.deleteChannel({ id, params: { bk_cloud_id } });
    this.deleteLoading = false;
    if (res) {
      this.$bkMessage({
        theme: 'success',
        message: this.$t('删除成功'),
      });
      this.handleDelete();
    }
  }
}
</script>

<style lang="postcss" scoped>
  .cloud-channel-tips {
    margin-top: 16px;
  }
  .delete-btn:hover {
    border-color: #ea3636;
    color: #ea3636;
  }
  .deploy-guide {
    margin-top: 16px;
    padding: 12px 20px 20px 20px;
    border-radius: 2px;
    background: #f9fafc;
    h3 {
      position: relative;
      margin: 0;
      &::before {
        content: "";
        position: absolute;
        top: 2px;
        left: -20px;
        display: block;
        padding: 2px;
        height: 10px;
        background: #c4c6cc;
      }
    }
    p + p {
      margin-top: 20px;
    }
  }
</style>
