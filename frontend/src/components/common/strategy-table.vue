<template>
  <bk-table show-overflow-tooltip :data="guideTable">
    <bk-table-column width="280" prop="source" :label="$t('源地址')" show-overflow-tooltip>
      <template #default="{ row }">
        <div v-if="row.sourceKey === 'agent'">
          <span>{{ row.source }}：</span>
          <template v-if="row.sourceRe">
            <div class="bk-tooltip" v-if=" detail[row.sourceKey]">
              <div class="cell-flex">
                <span class="cell-text" @click.stop="handleCopy(row.sourceKey)">
                  {{ detail[`${row.sourceKey}Str`] }}
                </span>
                <span v-if="detail[row.sourceKey] > 1">...</span>
                <span v-if="detail[row.sourceKey] > 1" class="num-tag">+{{ detail[row.sourceKey] }}</span>
                <i class="copy-icon nodeman-icon nc-copy-2" @click.stop="handleCopy(row.sourceKey)"></i>
              </div>
            </div>
            <span class="cell-placeholder" v-else>{{ hasCloud ? $t('请输入IP') : $t('请选择云区域') }}</span>
          </template>
        </div>
        <div class="cell-wrapper" v-else>
          <span>{{ row.source }}：</span>
          <bk-popover
            placement="top"
            :disabled="!(row.sourceKey === 'proxy' && notAvailableProxy)">
            <div class="cell-flex" v-if="detail[row.sourceKey]">
              <span class="cell-text" @click.stop="handleCopy(row.sourceKey)">
                {{ detail[`${row.sourceKey}Str`] }}
              </span>
              <span v-if="detail[row.sourceKey] > 1">...</span>
              <span v-if="detail[row.sourceKey] > 1" class="num-tag">+{{ detail[row.sourceKey] }}</span>
              <i class="copy-icon nodeman-icon nc-copy-2" @click.stop="handleCopy(row.sourceKey)"></i>
            </div>
            <span v-else-if="row.sourceKey === 'proxy' && notAvailableProxy" class="cell-placeholder">
              {{ $t('云区域未安装Proxy') }}
            </span>
            <span v-else-if="row.sourceRe" class="cell-placeholder">{{ row.source ? emptyPlaceholder : '' }}</span>
            <div slot="content">
              <bk-link v-if="notAvailableProxy" theme="primary" @click.stop="handleGotoProxy">{{$t('前往安装')}}</bk-link>
            </div>
          </bk-popover>
        </div>
      </template>
    </bk-table-column>
    <bk-table-column width="320" prop="targetAdress" :label="$t('目标地址')" show-overflow-tooltip>
      <template #default="{ row }">
        <div class="cell-wrapper">
          <div v-if="row.targetKey === 'agent'">
            <span>{{ row.targetAdress }}</span>
            <span v-if="row.targetRe">：</span>
            <template v-if="row.targetRe">
              <div class="bk-tooltip" v-if="detail[row.sourceKey]">
                <div class="cell-flex">
                  <span class="cell-text" @click.stop="handleCopy(row.targetKey)">
                    {{ detail[`${row.targetKey}Str`] }}
                  </span>
                  <span v-if="detail[row.targetKey] > 1">...</span>
                  <span v-if="detail[row.targetKey] > 1" class="num-tag">+{{ detail[row.targetKey] }}</span>
                  <i class="copy-icon nodeman-icon nc-copy-2" @click.stop="handleCopy(row.targetKey)"></i>
                </div>
              </div>
              <span v-else class="cell-placeholder">{{ hasCloud ? $t('请输入IP') : $t('请选择云区域') }}</span>
            </template>
          </div>
          <div class="cell-wrapper" v-else>
            <span>{{ row.targetAdress }}</span>
            <span v-if="row.targetRe">：</span>
            <bk-popover
              placement="top"
              :disabled="!(row.targetKey === 'proxy' && notAvailableProxy)">
              <div class="cell-flex" v-if="detail[row.targetKey]">
                <span class="cell-text" @click.stop="handleCopy(row.targetKey)">
                  {{ detail[`${row.targetKey}Str`] }}
                </span>
                <span v-if="detail[row.targetKey] > 1">...</span>
                <span v-if="detail[row.targetKey] > 1" class="num-tag">+{{ detail[row.targetKey] }}</span>
                <i class="copy-icon nodeman-icon nc-copy-2" @click.stop="handleCopy(row.targetKey)"></i>
              </div>
              <span v-else-if="row.targetKey === 'proxy' && notAvailableProxy" class="cell-placeholder">
                {{ $t('云区域未安装Proxy') }}
              </span>
              <span v-else-if="row.targetRe" class="cell-placeholder">
                {{ row.targetAdress ? emptyPlaceholder : '' }}
              </span>
              <div slot="content">
                <bk-link v-if="notAvailableProxy" theme="primary" @click.stop="handleGotoProxy">{{$t('前往安装')}}</bk-link>
              </div>
            </bk-popover>
          </div>
        </div>
      </template>
    </bk-table-column>
    <bk-table-column width="120" prop="port" :label="$t('端口')" show-overflow-tooltip>
      <template #default="{ row }">
        <div v-if="row.portKey">
          <span v-if="row.portKey === 'bt_range'" :class="{ 'cell-placeholder': !area.bt_port_start }">
            {{ area.bt_port_start ? `${area.bt_port_start}-${area.bt_port_end}` : $t('请选择云区域') }}
          </span>
          <bk-popover
            v-else-if="row.portKey === 'zk'"
            theme="light strategy-table"
            placement="top"
            :disabled="detail.zk < 2">
            <span
              :class="{ 'text-link': detail.zk > 1, 'cell-placeholder': !detail.zk }"
              @click.stop="handleCopy('zkHosts')">
              {{ detail.zkText }}
            </span>
            <ul slot="content">
              <li class="" v-for="ip in detail.zkHosts" :key="ip">{{ ip }}</li>
              <li class="mt5">
                <bk-link theme="primary" @click.stop="handleCopy('zkHosts')">{{ $t('点击复制') }}</bk-link>
              </li>
            </ul>
          </bk-popover>
          <span
            v-else-if="row.portKey"
            :class="{ 'cell-placeholder': !area[row.portKey] }">
            {{ area[row.portKey] || $t('请选择云区域') }}
          </span>
        </div>
        <span v-else-if="row.port">{{ row.port }}</span>
      </template>
    </bk-table-column>
    <bk-table-column width="110" prop="protocol" :label="$t('协议')" show-overflow-tooltip></bk-table-column>
    <bk-table-column prop="use" :label="$t('用途')" show-overflow-tooltip></bk-table-column>
  </bk-table>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';
import { copyText } from '@/common/util';

@Component({ name: 'StrategyTable' })
export default class StrategyTable extends Vue {
  @Prop({ type: Boolean, default: false }) private readonly hasCloud!: boolean;
  @Prop({ type: String, default: 'Agent' }) private readonly hostType!: string;
  @Prop({ type: Object, default: () => ({
    dataserver: [],
    taskserver: [],
    btfileserver: [],
    proxy: [],
    zk: [],
    zkHosts: [],
    agent: [],
  }) }) private readonly area!: { [key: string]: any[] };

  private sourceMap = ['Agent', 'GSE_btsvr'];
  private table: { [key: string]: any } = {
    Agent: [
      {
        source: 'Agent',
        targetAdress: this.$t('节点管理后台'),
        protocol: 'TCP',
        port: '80,443',
        use: this.$t('TCP上报日志获取配置'),
        sourceRe: true,
        sourceKey: 'agent',
      },
      {
        source: 'Agent',
        targetAdress: 'zk',
        protocol: 'TCP',
        portKey: 'zk',
        use: this.$t('获取配置'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'zk',
      },
      {
        source: 'Agent',
        targetAdress: 'GSE_task',
        protocol: 'TCP',
        portKey: 'io_port',
        use: this.$t('任务服务端口'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'taskserver',
      },
      {
        source: 'Agent',
        targetAdress: 'GSE_data',
        protocol: 'TCP',
        portKey: 'data_port',
        use: this.$t('数据上报端口'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'dataserver',
      },
      {
        source: 'Agent',
        targetAdress: 'GSE_btsvr',
        protocol: 'TCP',
        portKey: 'file_svr_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'btfileserver',
      },
      {
        source: 'Agent',
        targetAdress: 'GSE_btsvr',
        protocol: 'TCP,UDP',
        portKey: 'bt_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'btfileserver',
      },
      {
        source: 'Agent',
        targetAdress: 'GSE_btsvr',
        protocol: 'UDP',
        portKey: 'tracker_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'btfileserver',
      },
      {
        source: 'GSE_btsvr',
        targetAdress: 'Agent',
        protocol: 'TCP,UDP',
        portKey: 'bt_range',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'btfileserver',
        targetKey: 'agent',
      },
      {
        source: 'GSE_btsvr',
        targetAdress: 'GSE_btsvr',
        protocol: 'TCP',
        portKey: 'btsvr_thrift_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'btfileserver',
        targetKey: 'btfileserver',
      },
      {
        source: 'GSE_btsvr',
        targetAdress: 'GSE_btsvr',
        protocol: 'TCP,UDP',
        portKey: 'bt_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'btfileserver',
        targetKey: 'btfileserver',
      },
      {
        source: 'GSE_btsvr',
        targetAdress: 'GSE_btsvr',
        protocol: 'UDP',
        portKey: 'tracker_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'btfileserver',
        targetKey: 'btfileserver',
      },
      {
        source: 'Agent',
        targetAdress: 'Agent',
        protocol: 'TCP,UDP',
        portKey: 'bt_range',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'agent',
      },
      {
        source: 'Agent',
        targetAdress: '',
        protocol: '',
        port: this.$t('监听随机端口'),
        use: this.$t('BT传输可不开通'),
        sourceRe: true,
        sourceKey: 'agent',
      },
      {
        source: 'GSE_btsvr',
        targetAdress: '',
        protocol: '',
        port: this.$t('监听随机端口'),
        use: this.$t('BT传输可不开通'),
        sourceRe: true,
        sourceKey: 'btfileserver',
      },
    ],
    Pagent: [
      {
        source: 'Agent',
        targetAdress: 'Proxy',
        protocol: 'TCP',
        port: '17980,17981',
        portKey: '',
        use: this.$t('nginx下载nginx代理'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'proxy',
      },
      {
        source: 'Agent',
        targetAdress: 'Proxy(GSE_agent)',
        protocol: 'TCP',
        portKey: 'io_port',
        use: this.$t('任务服务端口'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'proxy',
      },
      {
        source: 'Agent',
        targetAdress: 'Proxy(GSE_transit)',
        protocol: 'TCP',
        portKey: 'data_port',
        use: this.$t('数据上报端口'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'proxy',
      },
      {
        source: 'Agent',
        targetAdress: 'Proxy(GSE_btsvr)',
        protocol: 'TCP',
        portKey: 'file_svr_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'proxy',
      },
      {
        source: 'Agent',
        targetAdress: 'Proxy(GSE_btsvr)',
        protocol: 'TCP,UDP',
        portKey: 'bt_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'proxy',
      },
      {
        source: 'Agent',
        targetAdress: 'Proxy(GSE_btsvr)',
        protocol: 'UDP',
        portKey: 'tracker_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'proxy',
      },
      {
        source: 'Proxy(GSE_btsvr)',
        targetAdress: 'Agent',
        protocol: 'TCP,UDP',
        portKey: 'bt_range',
        use: this.$t('BT传输'),
        sourceKey: 'proxy',
        targetKey: 'agent',
      },
      {
        source: 'Agent',
        targetAdress: 'Agent',
        protocol: 'TCP,UDP',
        portKey: 'bt_range',
        use: `${this.$t('BT传输')}${this.$t('同一子网')}`,
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'agent',
      },
      {
        source: 'Agent',
        targetAdress: '',
        protocol: '',
        port: this.$t('监听随机端口'),
        portKey: '',
        use: this.$t('BT传输可不开通'),
        sourceRe: true,
        sourceKey: 'agent',
      },
    ],
    Proxy: [
      {
        source: 'Proxy(GSE_agent)',
        targetAdress: 'GSE_task',
        protocol: 'TCP',
        portKey: 'io_port',
        use: this.$t('任务服务端口'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'taskserver',
      },
      {
        source: 'Proxy(GSE_transit)',
        targetAdress: 'GSE_data',
        protocol: 'TCP',
        portKey: 'data_port',
        use: this.$t('数据上报端口'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'dataserver',
      },
      {
        source: 'Proxy(GSE_btsvr)',
        targetAdress: 'GSE_btsvr',
        protocol: 'TCP',
        portKey: 'btsvr_thrift_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'btfileserver',
      },
      {
        source: 'Proxy(GSE_btsvr)',
        targetAdress: 'GSE_btsvr',
        protocol: 'TCP,UDP',
        portKey: 'bt_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'btfileserver',
      },
      {
        source: 'Proxy(GSE_btsvr)',
        targetAdress: 'GSE_btsvr',
        protocol: 'UDP',
        portKey: 'tracker_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'btfileserver',
      },
      {
        source: 'GSE_btsvr',
        targetAdress: 'Proxy(GSE_btsvr)',
        protocol: 'TCP',
        portKey: 'btsvr_thrift_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'btfileserver',
        targetKey: 'agent',
      },
      {
        source: 'GSE_btsvr',
        targetAdress: 'Proxy(GSE_btsvr)',
        protocol: 'TCP,UDP',
        portKey: 'bt_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'btfileserver',
        targetKey: 'agent',
      },
      {
        source: 'GSE_btsvr',
        targetAdress: 'Proxy(GSE_btsvr)',
        protocol: 'UDP',
        portKey: 'tracker_port',
        use: this.$t('BT传输'),
        sourceRe: true,
        targetRe: true,
        sourceKey: 'btfileserver',
        targetKey: 'agent',
      },
      {
        source: 'Proxy(GSE_btsvr)',
        targetAdress: 'Proxy(GSE_btsvr)',
        protocol: 'TCP',
        portKey: 'btsvr_thrift_port',
        use: `${this.$t('BT传输')}${this.$t('同一子网')}`,
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'agent',
      },
      {
        source: 'Proxy(GSE_btsvr)',
        targetAdress: 'Proxy(GSE_btsvr)',
        protocol: 'TCP,UDP',
        portKey: 'bt_port',
        use: `${this.$t('BT传输')}${this.$t('同一子网')}`,
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'agent',
      },
      {
        source: 'Proxy(GSE_btsvr)',
        targetAdress: 'Proxy(GSE_btsvr)',
        protocol: 'UDP',
        portKey: 'tracker_port',
        use: `${this.$t('BT传输')}${this.$t('同一子网')}`,
        sourceRe: true,
        targetRe: true,
        sourceKey: 'agent',
        targetKey: 'agent',
      },
      {
        source: 'Proxy(GSE_agent)',
        targetAdress: '',
        protocol: '',
        port: this.$t('监听随机端口'),
        use: this.$t('BT传输可不开通'),
        sourceRe: true,
        sourceKey: 'agent',
      },
      {
        source: 'Proxy(GSE_btsvr)',
        targetAdress: '',
        protocol: '',
        port: this.$t('监听随机端口'),
        use: this.$t('BT传输可不开通'),
        sourceRe: true,
        sourceKey: 'agent',
      },
    ],
  };
  private get guideTable() {
    return this.table[this.hostType];
  }
  private get detail(): { [key: string]: any } {
    return {
      /**
         * Agent: agent, zk, dataserver, taskserver, btfileserver
         * Pagent: agent, proxy
         * Proxy: proxy, dataserver, taskserver, btfileserver
         */
      agentStr: this.area.agent[0],
      agent: this.area.agent.length,
      zkHosts: this.area.zkHosts.map(item => (`${item.zk_ip}:${item.zk_port}`)),
      zkStr: this.area.zk[0],
      zk: this.area.zk.length,
      // eslint-disable-next-line no-nested-ternary
      zkText: this.area.zk.length > 1
        ? this.$t('详情') : (this.area.zk.length ? this.area.zkHosts[0].zk_port : this.$t('请选择云区域')),
      dataserverStr: this.area.dataserver[0],
      dataserver: this.area.dataserver.length,
      taskserverStr: this.area.dataserver[0],
      taskserver: this.area.taskserver.length,
      btfileserverStr: this.area.btfileserver[0],
      btfileserver: this.area.btfileserver.length,
      proxyStr: this.area.proxy[0],
      proxy: this.area.proxy.length,
    };
  }
  // 云区域下无可用的proxy
  private get notAvailableProxy() {
    return this.hostType === 'Pagent' && (this.area.bk_cloud_id || this.area.bk_cloud_id === 0) && !this.detail.proxy;
  }
  private get emptyPlaceholder() {
    return this.hostType === 'Proxy' ? this.$t('请输入IP') : this.$t('请选择接入点');
  }

  private handleCopy(str: string) {
    if (this.detail[str]) {
      const data = str === 'zkHosts' ? this.detail.zkHosts : this.area[str];
      copyText(data.join('\n'), () => {
        this.$bkMessage({ theme: 'success', message: this.$t('IP复制成功', { num: data.length }) });
      });
    }
  }
  private handleGotoProxy() {
    if (this.area.bk_cloud_id || this.area.bk_cloud_id === 0) {
      this.$router.push({
        name: 'setupCloudManager',
        params: {
          type: 'create',
          title: window.i18n.t('安装Proxy'),
          id: this.area.bk_cloud_id,
        },
      });
    }
  }
}
</script>
<style lang="scss" scoped>
  .cell-wrapper {
    display: flex;
    align-items: center;
    line-height: 16px;
  }
  .cell-flex {
    display: flex;
    position: relative;
    padding-right: 20px;
    .num-tag {
      margin: 0 4px;
      display: inline-block;
      padding: 1px 4px;
      line-height: 12px;
      border-radius: 8px;
      color: #979ba5;
      background: #ebedf5;
      transform: scale(.8);
    }
    .copy-icon {
      position: absolute;
      top: -1px;
      right: 2px;
      display: none;
      font-size: 16px;
      cursor: pointer;
    }
    &:hover {
      color: #3a84ff;
      .num-tag {
        background: #e1ecff;
      }
      .copy-icon {
        display: block;
      }
    }
  }
  .cell-placeholder {
    color: #c4c6cc;
  }
  .cell-text {
    flex: 1;
    cursor: pointer;
  }
  .text-link {
    color: #3a84ff;
    cursor: pointer;
  }
</style>
