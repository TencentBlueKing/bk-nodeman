<template>
  <div>
    <table class="access-point-table">
      <thead>
        <tr>
          <th with="125"></th>
          <th with="100"></th>
          <th with="100"></th>
          <th with="735"></th>
        </tr>
      </thead>
      <tbody>
        <!-- Server信息 -->
        <tr>
          <td :rowspan="rowspanNum.servers">{{ $t('Server信息') }}</td>
          <td rowspan="2">{{ $t('地域信息') }}</td>
          <td>{{ $t('区域') }}</td>
          <td class="table-content">{{ formData.region_id | filterEmpty }}</td>
        </tr>
        <tr>
          <td>{{ $t('城市') }}</td>
          <td class="table-content">{{ formData.city_id | filterEmpty }}</td>
        </tr>
        <tr>
          <td>Zookeeper</td>
          <td>{{ $t('集群地址') }}</td>
          <td class="table-content">{{ zookeeper }}</td>
        </tr>
        <template v-for="(str, idx) in serversSets">
          <tr v-for="(server, index) in formData[str]" :key="`server${idx + index}`">
            <td>{{ `${str} ${ index + 1 }` }}</td>
            <td>IP</td>
            <td class="table-content">{{ `${ $t('内网') + server.inner_ip };  ${ $t('外网') + server.outer_ip }` }}</td>
          </tr>
        </template>
        <tr>
          <td>{{ $t('外网回调') }}</td>
          <td>URL</td>
          <td class="table-content">
            {{ formData.outer_callback_url | filterEmpty }}
          </td>
        </tr>
        <tr>
          <td rowspan="2">{{ $t('Agent安装包') }}</td>
          <td>URL</td>
          <td class="table-content">
            {{ `${ $t('内网') + formData.package_inner_url };  ${ $t('外网') + formData.package_outer_url }` }}
          </td>
        </tr>
        <tr>
          <td>{{ $t('服务器目录') }}</td>
          <td class="table-content">{{ formData.nginx_path | filterEmpty }}</td>
        </tr>
        <!-- Agent信息 - Linux -->
        <template v-if="rowspanNum.linux">
          <tr v-for="(path, index) in formData.linux" :key="index + 100">
            <td v-if="index === 0" :rowspan="rowspanNum.agent">{{ $t('Agent信息') }}</td>
            <td v-if="index === 0" :rowspan="rowspanNum.linux">Linux</td>
            <td>{{ path.name }}</td>
            <td class="table-content">{{ path.value }}</td>
          </tr>
        </template>
        <!-- Agent信息 - Windows -->
        <template v-if="rowspanNum.windows">
          <tr v-for="(path, index) in formData.windows" :key="index + 200">
            <td v-if="index === 0" :rowspan="rowspanNum.windows">Windows</td>
            <td>{{ path.name }}</td>
            <td class="table-content">{{ path.value }}</td>
          </tr>
        </template>
        <!-- Proxy 信息 -->
        <template v-if="rowspanNum.proxy">
          <tr>
            <td colspan="2" class="tc">{{ $t('Proxy信息') }}</td>
            <td>{{ $t('安装包') }}</td>
            <td class="table-content">{{ formData.proxy_package.join('; ') }}</td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { IApExpand, IZk } from '@/types/config/config';

type IServer = 'BtfileServer' | 'DataServer' | 'TaskServer';

@Component({ name: 'AccessPointTable' })

export default class AccessPointTable extends Vue {
  @Prop({ type: Object, default: () => ({}) }) private readonly accessPoint!: IApExpand;

  private pathMap: { [key: string]: string } = {
    dataipc: 'dataipc',
    setup_path: window.i18n.t('安装路径'),
    hostid_path: window.i18n.t('hostid路径'),
    data_path: window.i18n.t('数据文件路径'),
    run_path: window.i18n.t('运行时路径'),
    log_path: window.i18n.t('日志文件路径'),
    temp_path: window.i18n.t('临时文件路径'),
  };
  private serversSets =['BtfileServer', 'DataServer', 'TaskServer'];
  private serversOtherKeys = ['region_id', 'city_id', 'zookeeper', 'outer_callback_url', 'package__url', 'nginx_path'];
  private  sortLinux = ['hostid_path', 'dataipc', 'setup_path', 'data_path', 'run_path', 'log_path'];
  private sortWin = ['hostid_path', 'dataipc', 'setup_path', 'data_path', 'run_path', 'log_path'];
  private formData = {};

  // 将表格rowspan的值计算出来
  private get rowspanNum(): { [key: string]: number } {
    const linux = this.sortLinux.length;
    const windows = this.sortWin.length;
    const tableRow = {
      servers: this.serversOtherKeys.length,
      agent: linux + windows,
      linux,
      windows,
      proxy: this.accessPoint.proxy_package.length ? 1 : 0,
    };
    this.serversSets.forEach((item) => {
      tableRow.servers += this.accessPoint[item as keyof IApExpand]
        ? this.accessPoint[item as IServer].length : 0;
    });
    return tableRow;
  }
  private get zookeeper(): string {
    if (this.accessPoint.zk_hosts) {
      return this.accessPoint.zk_hosts.map((host: IZk) => `${host.zk_ip}:${host.zk_port}`).join(',');
    }
    return '';
  }

  private created() {
    this.resetData();
  }

  private  resetData() {
    // agent_config 需要按顺序排序
    const { agent_config: { linux, windows } } = this.accessPoint;
    const sortLinux = this.sortLinux.map(item => ({
      name: this.pathMap[item],
      value: linux[item],
    }));
    const sortWindows = this.sortWin.map(item => ({
      name: this.pathMap[item],
      value: windows[item],
    }));
    this.formData = Object.assign({}, this.accessPoint, { linux: sortLinux, windows: sortWindows });
  }
}
</script>

<style lang="postcss">
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
  }
  .table-content {
    color: #63656e;
  }
}
</style>
