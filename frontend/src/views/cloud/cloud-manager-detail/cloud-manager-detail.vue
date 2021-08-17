<template>
  <article class="cloud-manager-detail">
    <!--详情左侧面板-->
    <CloudDetailNav :is-first="isFirst" :id="navActiveId" :search="search"></CloudDetailNav>
    <!--右侧表格-->
    <section class="detail-right pt20">
      <!--自定义三级导航-->
      <section class="detail-right-head">
        <div class="detail-right-title mb20">
          <i class="title-icon nodeman-icon nc-back-left" @click="handleRouteBack"></i>
          <span class="title-name">{{ navTitle }}</span>
        </div>
        <GapTab
          addable
          controllable
          :loading="channelLoading"
          :list="tabList"
          v-model="tabActive"
          @add-tab="handleShowChannelSlider()">
        </GapTab>
      </section>

      <!--表格-->
      <div class="detail-right-content mt20">
        <CloudDetailTable
          v-show="tabActive === 'default'"
          :loading="loadingProxy"
          :id="navActiveId"
          :proxy-data="proxyData"
          @reload-proxy="handleGetProxyList">
        </CloudDetailTable>
        <CloudChannel
          v-for="(channel, index) in channelList"
          v-show="tabActive === channel.id"
          :key="index"
          :channel="channel"
          @channel-edit="handleShowChannelSlider(channel, true)"
          @channel-delete="handleChannelConfirm">
        </CloudChannel>
      </div>

      <ChannelEdit
        v-model="showEditChannel"
        :channel="currentChannel"
        :cloud-id="navActiveId"
        :edit="editChannel"
        @channel-confirm="handleChannelConfirm">
      </ChannelEdit>
    </section>
  </article>
</template>
<script lang="ts">
import { Component, Prop, Watch, Mixins } from 'vue-property-decorator';
import { MainStore, CloudStore, AgentStore } from '@/store/index';
import { isEmpty } from '@/common/util';
import CloudDetailNav from './cloud-detail-nav.vue';
import CloudChannel from '../cloud-channel/index.vue';
import ChannelEdit from '../cloud-channel/channel-edit.vue';
import CloudDetailTable from './cloud-detail-table.vue';
import GapTab from './GapTab.vue';
import pollMixin from '@/common/poll-mixin';
import routerBackMixin from '@/common/router-back-mixin';
import { IProxyDetail } from '@/types/cloud/cloud';

@Component({
  name: 'CloudManagerDetail',
  components: {
    CloudDetailNav,
    CloudChannel,
    ChannelEdit,
    CloudDetailTable,
    GapTab,
  },
})


export default class CloudManagerDetail extends Mixins(pollMixin, routerBackMixin) {
  @Prop({ type: [Number, String], default: 0 }) private readonly id!: string | number;
  @Prop({ type: Boolean, default: true }) private readonly isFirst!: boolean; // 是否是首次加载
  @Prop({ type: String, default: '' }) private readonly search!: string;

  private navActiveId = parseInt(this.id as string, 10);
  private bkCloudName = this.search; // 别名
  private proxyData: IProxyDetail[] = []; // proxy表格数据
  private channelLoading = false;
  // Proxy列表加载
  private loadingProxy = false;
  private firstLoad = this.isFirst;
  private tabActive = 'default';
  private tabList: Dictionary[] = [
    { label: window.i18n.t('默认通道'), id: 'default' },
  ];
  private showEditChannel = false;
  private currentChannel: Dictionary = {};
  private editChannel = false;
  private channelList: any[] = [];

  private get permissionSwitch() {
    return MainStore.permissionSwitch;
  }
  private get cloudList() {
    return CloudStore.cloudList;
  }
  // 导航title
  private get navTitle() {
    const list = this.permissionSwitch ? this.cloudList.filter(item => item.view) : this.cloudList;
    const cloudArea = list.find(item => item.bkCloudId === this.navActiveId);
    return cloudArea ? cloudArea.bkCloudName : this.$t('未选中云区域');
  }

  @Watch('id')
  private handleIdChange(newValue: string, oldValue: string) {
    if (!isEmpty(newValue) && parseInt(newValue, 10) !== parseInt(oldValue, 10)) {
      this.navActiveId = parseInt(newValue, 10);
      this.tabActive = 'default';
      this.handleGetProxyList();
      this.getChannelData();
    }
  }
  private created() {
    this.handleGetProxyList();
    this.getChannelData();
  }
  /**
     * 获取云区域Proxy列表
     */
  public async handleGetProxyList(loading = true) {
    this.loadingProxy = loading;
    this.proxyData = await CloudStore.getCloudProxyList({ bk_cloud_id: this.navActiveId });
    this.runingQueue = [];
    const isRunning = this.proxyData.some(item => item.job_result && item.job_result.status === 'RUNNING');
    if (isRunning) {
      this.runingQueue.push(this.navActiveId);
    }
    this.loadingProxy = false;
  }
  public async getChannelData() {
    this.tabList.splice(1, this.tabList.length - 1);
    this.channelLoading = true;
    const list: any[] = await CloudStore.getChannelList();
    const tabList: any[] = [];
    let ips: string[] = [];
    const channelList = list.filter(item => item.bk_cloud_id === this.navActiveId)
      .map(item => ({ ...item, status: '' }));
    channelList.forEach((item) => {
      ips = ips.concat(item.jump_servers || []);
      tabList.push({ id: item.id, label: item.name });
    });
    this.channelList = channelList;
    this.tabList.splice(1, this.tabList.length - 1, ...tabList);
    this.getChannelStatus(ips);
    this.channelLoading = false;
  }
  // 同步作为安装通道的主机状态
  public async getChannelStatus(ips: string[]) {
    const params = {
      pagesize: 50,
      page: 1,
      conditions: [
        { key: 'inner_ip', value: Array.from(new Set(ips)) },
        { key: 'bk_cloud_id', value: [this.navActiveId] },
      ],
      extra_data: ['job_result', 'identity_info'],
    };
    const { list } = await AgentStore.getHostList(params);
    if (list.length) {
      this.channelList.forEach((item) => {
        const { bk_cloud_id: cloudId, jump_servers: [jumpServers] = [''] } = item;
        const host = list.find((host: Dictionary) => host.bk_cloud_id === cloudId && host.inner_ip === jumpServers);
        if (host) {
          item.status = host.status;
        }
      });
    }
  }
  /**
     * 处理轮询的数据
     */
  public async handlePollData() {
    await this.handleGetProxyList(false);
  }
  /**
     * 返回上一层路由
     */
  public handleRouteBack() {
    this.routerBack();
  }
  public handleTabChange(id: string) {
    this.tabActive = id;
  }
  public handleShowChannelSlider(channel: Dictionary, edit: boolean) {
    this.editChannel = !!edit;
    this.showEditChannel = true;
    this.currentChannel = channel || {};
  }
  public handleChannelConfirm({ channel, type = 'add' }: { channel: Dictionary, type: 'add' | 'delete' }) {
    const index = this.channelList.findIndex(item => item.id === channel.id);
    const { id, name, jump_servers: jumpServers } = channel;
    if (type === 'add') {
      const channelTab = { id, label: name };
      if (index > -1) {
        const copyChannel = Object.assign({}, this.channelList[index + 1], channel);
        this.channelList.splice(index, 1, copyChannel);
        this.tabList.splice(index + 1, 1, channelTab);
      } else {
        this.channelList.push(Object.assign({ status: '' }, channel));
        this.tabList.push(channelTab);
        this.tabActive = id;
      }
    } else {
      this.channelList.splice(index, 1);
      this.tabList.splice(index + 1, 1);
      if (this.tabActive === channel.id) {
        this.tabActive = 'default';
      }
    }
    // 同步修改或新增的主机状态
    this.getChannelStatus(jumpServers);
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

.cloud-manager-detail {
  height: calc(100vh - 52px);

  @mixin layout-flex row;
  .detail-right {
    flex: 1;
    border-left: 1px solid #dcdee5;
    width: calc(100% - 240px);
    overflow-y: auto;
    &-head {
      background: #fafbfd;
    }
    &-content {
      padding: 0 24px;
    }
    &-title {
      padding: 0 24px;
      line-height: 20px;

      @mixin layout-flex row;
      .title-icon {
        position: relative;
        top: -4px;
        height: 20px;
        font-size: 28px;
        color: #3a84ff;
        cursor: pointer;
      }
      .title-name {
        font-size: 16px;
        color: #313238;
      }
    }
  }
}
</style>
