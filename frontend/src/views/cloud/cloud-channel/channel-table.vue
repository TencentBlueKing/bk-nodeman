<template>
  <table class="channel-table">
    <colgroup width="120"></colgroup>
    <colgroup width="140"></colgroup>
    <colgroup></colgroup>
    <thead>
      <tr>
        <th class="head-th" colspan="3">
          <div class="col-status">
            <span :class="`status-mark status-${channel.status}`"></span>
            <span>{{ channel.jump_servers.join(',') }}</span>
          </div>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(server, index) in serverList" :key="index">
        <td class="title-td" v-if="index === 0" :rowspan="channelServerKeys.length">{{ $t("上游节点") }}</td>
        <td class="title-td">{{ server.key }}</td>
        <td>{{ server.value }}</td>
      </tr>
      <template v-if="showAdvancedConfig">
        <tr>
          <td class="title-td" colspan="2">
            <span class="text-underline" v-bk-tooltips="{
              width: 200,
              placement: 'top-start',
              content: $t('通道上游节点tips'),
            }">{{ $t("通道上游节点") }}</span>
          </td>
          <td class="title-td">{{ channel.upstream_servers.channel_proxy_address | filterEmpty }}</td>
        </tr>
      </template>
    </tbody>
  </table>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { CloudStore } from '@/store';

@Component
export default class ChannelTable extends Vue {
  @Prop({ default: () => ({}), type: Object }) private readonly channel!: Dictionary;

  private get channelServerKeys() {
    return CloudStore.channelServerKeys;
  }
  private get serverList() {
    const { upstream_servers: servers = {} } = this.channel;
    return this.channelServerKeys.map(key => ({
      key,
      value: servers[key] ? servers[key].join(';') : '',
    }));
  }
  private get showAdvancedConfig() {
    return !!this.channel.upstream_servers.channel_proxy_address;
  }
}
</script>

<style lang="postcss" scoped>
  .channel-table {
    width: 100%;
    th,
    td {
      padding: 10px 16px;
      line-height: 21px;
      border: 1px solid #dcdee5;
      color: #63656e;
    }
    .head-th {
      text-align: left;
      font-weight: 700;
      color: #313238;
      background: #fafbfd;
    }
    .title-td {
      padding: 10px 20px;
      color: #313238;
    }
  }
</style>
