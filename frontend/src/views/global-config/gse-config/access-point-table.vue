<template>
  <div class="ap-table-wrapper">
    <table class="access-point-table">
      <thead>
        <tr>
          <th with="225"></th>
          <th with="100"></th>
          <th with="735"></th>
        </tr>
      </thead>
      <tbody>
        <!-- Server信息 -->
        <tr>
          <td colspan="3" class="ap-info-title">{{ $t('Server信息') }}</td>
        </tr>
        <tr>
          <td colspan="2">{{ $t('区域') }}</td>
          <td class="table-content">{{ formData.region_id }}</td>
        </tr>
        <tr>
          <td colspan="2">{{ $t('城市') }}</td>
          <td class="table-content">{{ formData.city_id }}</td>
        </tr>
        <tr>
          <td colspan="2">{{ $t('Zookeeper集群地址') }}</td>
          <td class="table-content">{{ zookeeper }}</td>
        </tr>
        <template v-for="server in serversSets">
          <tr :key="`${server.id}_inner_ip_infos`">
            <td rowspan="2">{{ server.name }}</td>
            <td>{{ $t('内网IP') }}</td>
            <td class="table-content">
              {{ formData[server.id]?.inner_ip_infos.map(item => item.ip).join('; ') || '--' }}
            </td>
          </tr>
          <tr :key="`${server.id}_outer_ip_infos`">
            <td>{{ $t('外网IP') }}</td>
            <td class="table-content">
              {{ formData[server.id]?.outer_ip_infos.map(item => item.ip).join('; ') || '--' }}
            </td>
          </tr>
        </template>
        <tr>
          <td rowspan="2">{{ $t('回调地址') }}</td>
          <td>{{ $t('内网URL') }}</td>
          <td class="table-content">{{ formData.callback_url || '--' }}</td>
        </tr>
        <tr>
          <td>{{ $t('外网URL') }}</td>
          <td class="table-content">{{ formData.outer_callback_url || '--' }}</td>
        </tr>
        <tr>
          <td rowspan="3">{{ $t('Agent安装包信息') }}</td>
          <td>{{ $t('内网URL') }}</td>
          <td class="table-content">{{ formData.package_inner_url || '--' }}</td>
        </tr>
        <tr>
          <td>{{ $t('外网URL') }}</td>
          <td class="table-content">{{ formData.package_outer_url || '--' }}</td>
        </tr>
        <tr>
          <td>{{ $t('服务器目录') }}</td>
          <td class="table-content">{{ formData.nginx_path || '--' }}</td>
        </tr>
      </tbody>
      <!-- Agent信息 - Linux -->
      <tbody>
        <tr>
          <td colspan="3" class="ap-info-title">{{ $t('Agent信息') }}</td>
        </tr>
        <template v-if="rowspanNum.linux">
          <tr v-for="(path, index) in formData.linux" :key="index + 100">
            <!-- <td v-if="index === 0" :rowspan="rowspanNum.agent">{{ $t('Agent信息') }}</td> -->
            <td v-if="index === 0" :rowspan="rowspanNum.linux">Linux</td>
            <td class="label-td">{{ path.name }}</td>
            <td class="table-content">{{ path.value }}</td>
          </tr>
        </template>
        <!-- Agent信息 - Windows -->
        <template v-if="rowspanNum.windows">
          <tr v-for="(path, index) in formData.windows" :key="index + 200">
            <td v-if="index === 0" :rowspan="rowspanNum.windows">Windows</td>
            <td class="label-td">{{ path.name }}</td>
            <td class="table-content">{{ path.value }}</td>
          </tr>
        </template>
      </tbody>

      <!-- Proxy 信息 -->
      <tbody>
        <tr>
          <td colspan="3" class="ap-info-title">{{ $t('Proxy信息') }}</td>
        </tr>
        <template v-if="rowspanNum.proxy">
          <tr>
            <td colspan="2" class="tc">{{ $t('Proxy安装包') }}</td>
            <td class="table-content">{{ formData.proxy_package.join('; ') }}</td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script lang="ts" setup>
import { computed, getCurrentInstance, reactive, ref } from 'vue';
import { IApExpand, IZk } from '@/types/config/config';
import { regIPv6 } from '@/common/regexp';
import i18n from '@/setup';
import { TranslateResult } from 'vue-i18n';

type IServer = 'BtfileServer' | 'DataServer' | 'TaskServer';

const proxy = getCurrentInstance()?.proxy;

const { accessPoint } = withDefaults(defineProps<{
  accessPoint: IApExpand
}>(), {});

const serversSets = ref<{ id: IServer; name: TranslateResult }[]>([
  { id: 'BtfileServer', name: i18n.t('GSE File服务地址') },
  { id: 'DataServer', name: i18n.t('GSE Data服务地址') },
  { id: 'TaskServer', name: i18n.t('GSE Cluster服务地址') },
]);

const state = reactive<{
  pathMap: { [key: string]: string|TranslateResult };
  sortLinux: string[];
  sortWin: string[]
}>({
  pathMap: {
    dataipc: 'dataipc',
    setup_path: i18n.t('安装路径'),
    hostid_path: i18n.t('hostid路径'),
    data_path: i18n.t('数据文件路径'),
    run_path: i18n.t('运行时路径'),
    log_path: i18n.t('日志文件路径'),
    temp_path: i18n.t('临时文件路径'),
  },
  sortLinux: ['hostid_path', 'dataipc', 'setup_path', 'data_path', 'run_path', 'log_path'],
  sortWin: ['hostid_path', 'dataipc', 'setup_path', 'data_path', 'run_path', 'log_path'],
});
const formData = reactive<IApExpand>({});

// 将表格rowspan的值计算出来
const rowspanNum = computed<{ [key: string]: number }>(() => {
  const linux = state.sortLinux.length;
  const windows = state.sortWin.length;
  const tableRow = {
    agent: linux + windows,
    linux,
    windows,
    proxy: accessPoint.proxy_package.length ? 1 : 0,
  };
  return tableRow;
});
const zookeeper = computed(() => {
  if (accessPoint.zk_hosts) {
    return accessPoint.zk_hosts.map((host: IZk) => (proxy?.$DHCP && regIPv6.test(host.zk_ip)
      ? `[${host.zk_ip}]:${host.zk_port}`
      : `${host.zk_ip}:${host.zk_port}`)).join(',');
  }
  return '';
});

const created = () => {
  // agent_config 需要按顺序排序
  const { agent_config: { linux, windows } } = accessPoint;
  const sortLinux = state.sortLinux.map(item => ({
    name: state.pathMap[item],
    value: linux[item],
  }));
  const sortWindows = state.sortWin.map(item => ({
    name: state.pathMap[item],
    value: windows[item],
  }));
  Object.assign(formData, accessPoint, { linux: sortLinux, windows: sortWindows });
};
created();

defineExpose({
  serversSets,
  rowspanNum,
  zookeeper,
});

</script>

<style lang="postcss">
.ap-table-wrapper {
  padding: 0 40px 20px 40px;
  border: 1px solid #dcdee5;
  border-bottom: 0;

  .ap-info-title {
    padding: 10px 0;
    height: 60px;
    margin-bottom: 12px;
    font-weight: bold;
    font-size: 14px;
    background-color: #fff;
    text-align: left;
    color: #313238;
    border-left: 0;
    border-right: 0;
    &:first-child {
      border-top: 0;
    }
  }
}

.access-point-table {
  width: 100%;
  color: #313238;
  thead {
    display: none;
  }
  th,
  td {
    padding: 10px 15px;
    line-height: 21px;
    border: 1px solid #dcdee5;
    background-color: #f5f7fa;
    text-align: center;
  }
  .table-content {
    text-align: left;
    color: #63656e;
    background-color: #fff;
  }
  .label-td {
    white-space: nowrap;
  }
  & + .ap-info-title {
    margin-top: 12px;
  }
}
</style>
