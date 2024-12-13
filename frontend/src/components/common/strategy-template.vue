<template>
  <div class="operation-tips">
    <p
      class="operation-step"
      v-for="(item, index) in tipList"
      :key="`operation${index}`">
      {{ `${ index + 1 }. ${ item }` }}
    </p>
    <div class="cloud-panel" v-if="this.cloudAreaList.length">
      <template v-if="hostType !== 'Agent'">
        <RightPanel
          v-for="cloudArea in cloudAreaList"
          :key="`${cloudArea.bk_cloud_id}_${cloudArea.ap_id}`"
          :class="['cloud-panel-item', { 'is-close': !cloudArea.collapse }]"
          :need-border="false"
          :icon-style="{ padding: '4px 4px', fontSize: '12px' }"
          collapse-color="#979BA5"
          title-bg-color="#F0F1F5"
          :collapse="cloudArea.collapse"
          :type="`${cloudArea.bk_cloud_id}_${cloudArea.ap_id}`"
          @change="handleToggle">
          <div class="collapse-header" slot="title">
            {{ `${ cloudArea.bk_cloud_name } - ${ cloudArea.ap_name }` }}
          </div>
          <div class="collapse-container" slot>
            <StrategyTable
              :has-cloud="!!cloudArea.bk_cloud_name"
              :host-type="cloudArea.type"
              :area="cloudArea">
            </StrategyTable>
          </div>
        </RightPanel>
      </template>
    </div>
    
  </div>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';
import { AgentStore } from '@/store/index';
import RightPanel from '@/components/common/right-panel.vue';
import StrategyTable from '@/components/common/strategy-table.vue';
import { isEmpty } from '@/common/util';
import { IApExpand } from '@/types/config/config';
import { IAgent } from '@/types/agent/agent-type';

@Component({
  name: 'StrategyTemplate',
  components: {
    StrategyTable,
    RightPanel,
  },
})
export default class StrategyTemplate extends Vue {
  @Prop({ type: String, default: 'Agent' }) private readonly hostType!: string;
  // key => bk_cloud_id、inner_ip、bk_cloud_name (ap_id、ap_name)
  @Prop({ type: Array, default: () => [] }) private readonly hostList!: any[];
  
  private loading = true;
  private cloudAreaList: any[] = [];

  private get tipList() {

    if (this.hostType === 'Proxy') {
      return [
        this.$t('Agent安装Tip1'),
        this.$t('Agent安装Tip2'),
        this.$t('Agent安装Tip3'),
      ];
    }
    return [
      this.$t('Proxy安装Tip1'),
      this.$t('Proxy安装Tip2'),
    ];
  }

  private async mounted() {
    if (!AgentStore.apList.length) {
      await AgentStore.getApList();
    }
    if (!AgentStore.cloudList.length) {
      AgentStore.getCloudList();
    }
    this.formatData();
  }

  private formatData() {
    const cloudMap = this.hostList.reduce((obj, item) => {
      const idKey = item.bk_cloud_id;
      const cloud = AgentStore.cloudList.find(child => child.bk_cloud_id === item.bk_cloud_id);
      // eslint-disable-next-line camelcase
      const proxy = cloud?.proxy_count ? cloud.proxies : [];
      let type = '';
      if (this.hostType === 'Proxy') {
        type = 'Proxy';
      } else {
        type = item.bk_cloud_id === window.PROJECT_CONFIG.DEFAULT_CLOUD ? 'Agent' : 'Pagent';
      }
      if (!isEmpty(idKey) && item.bk_cloud_name) {
        const copyItem = Object.assign({ type, proxy }, item);
        if (Object.prototype.hasOwnProperty.call(obj, idKey)) {
          obj[idKey].push(copyItem);
        } else {
          obj[idKey] = [copyItem];
        }
      }
      return obj;
    }, {});
        let collapse = true;
    // 填充 接入点信息、proxy信息、端口信息
    this.cloudAreaList = Object.values(cloudMap).reduce((arr: any[], children: any) => {
      const apMap: IAgent = {};
      children.forEach((cloud: any) => {
        let idKey = cloud.ap_id;
        let ap = AgentStore.apList.find(apItem => apItem.id === idKey) as IApExpand;

        const serverKey = cloud.type === 'Agent' ? 'inner_ip' : 'outer_ip'; // Pagent 非必要
        const proxyKey = cloud.type === 'Proxy' ? 'outer_ip' : 'inner_ip'; // Agent 非必要
        // 先排除掉找不到接入点的主机
        if (ap) {
          if (ap.id === -1 || AgentStore.apList.length === 2) {
            ap = AgentStore.apList.find(item => item.id !== -1) as IApExpand;
            idKey = ap.id;
          }
          if (Object.prototype.hasOwnProperty.call(apMap, idKey)) {
            cloud[proxyKey] && apMap[idKey].agent.push(cloud[proxyKey]);
          } else {
            ap.port_config = ap.port_config || {};
            apMap[idKey] = {
              collapse: collapse || false,
              type: cloud.type,
              bk_cloud_id: cloud.bk_cloud_id,
              bk_cloud_name: cloud.bk_cloud_name,
              ap_id: idKey,
              ap_name: ap.name,
              zk: ap.zk_hosts?.map(zk => zk.zk_ip) || [], // 仅Agent
              zkHosts: ap.zk_hosts,
              btfileserver: ap.btfileserver[serverKey]?.map(item => item.ip) || [],
              dataserver: ap.btfileserver[serverKey]?.map(item => item.ip) || [],
              taskserver: ap.btfileserver[serverKey]?.map(item => item.ip) || [],
              proxy: cloud.proxy?.map((item: any) => item[proxyKey]) || [],
              agent: cloud[proxyKey] ? [cloud[proxyKey]] : [], // Proxy 非必要
              ...ap.port_config,
            };
          }
          collapse = false;
        }
      });
      Object.values(apMap).reduce((arrChild, item) => {
        arrChild.push(item);
        return arrChild;
      }, arr);
      return arr;
    }, []);
    console.log("🚀 ~ StrategyTemplate ~ this.cloudAreaList=Object.values ~ this.cloudAreaList:", this.cloudAreaList)
    
  }
  /**
   * 手风琴模式
   */
  private handleToggle({ value, type }: { value: boolean, type: string }) {
    this.cloudAreaList.forEach((item) => {
      item.collapse = `${item.bk_cloud_id}_${item.ap_id}` === type ? value : false;
    });
  }
}
</script>
<style lang="scss" scoped>
  .operation-step {
    line-height: 24px;
  }
  .cloud-panel {
    margin-top: 14px;
    border-top: 1px solid #dcdee5;
    border-left: 1px solid #dcdee5;
    border-right: 1px solid #dcdee5;
    .collapse-header {
      font-size: 14px;
      font-weight: 700;
      color: #63656e;
    }
    .cloud-panel-item.is-close {
      border-bottom: 1px solid #dcdee5;
    }
  }
</style>
