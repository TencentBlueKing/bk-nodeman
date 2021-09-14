<template>
  <div class="plugin-detail"
       v-test="'pluginDetail'"
       v-bkloading="{ isLoading: loading }"
       v-freezing-page="{
         disabled: pluginInfo.is_ready,
         include: ['.detail-info', '.plugin-detail-content'],
         exclude: ['.content-icon', '.content-header', '.content-separator','.content-desc','.detail-operate']
       }">
    <section class="plugin-detail-header">
      <div class="nodeman-navigation-content">
        <span class="content-icon" @click="routerBack">
          <i class="nodeman-icon nc-back-left"></i>
        </span>
        <span class="content-header">{{ pluginInfo.name }}</span>
        <span class="content-separator">-</span>
        <template v-if="!aliasEdit">
          <span class="content-desc">{{ pluginInfo.description }}</span>
          <auth-component
            v-if="pluginInfo.is_ready"
            tag="i"
            class="nodeman-icon nc-icon-edit-2 content-edit"
            :authorized="packageOperateAuth"
            :apply-info="[authInfo]"
            @click="handleEditDesc">
          </auth-component>
          <span class="status-label" v-else>{{ $t('停用') }}</span>
        </template>
        <template v-else>
          <bk-input
            :value="pluginInfo.description"
            ref="aliasInput"
            class="description-name"
            size="small"
            @enter="handleConfirmEdit">
          </bk-input>
          <span class="alias-edit ml5" @click="handleConfirmEdit">
            <i class="nodeman-icon nc-check-small"></i>
          </span>
          <span class="alias-edit" @click="handleCancelEdit">
            <i class="nodeman-icon nc-delete"></i>
          </span>
        </template>
      </div>
      <div class="header-container">
        <div class="detail-info">
          <ul class="detail-info-list">
            <li class="list-item">
              <label>{{$t('开发商')}}</label>
              <span>{{pluginInfo.category | filterEmpty}}</span>
            </li>
            <li class="list-item">
              <label>{{$t('数据对接SaaS')}}</label>
              <span>{{pluginInfo.source_app_code | filterEmpty}}</span>
            </li>
            <li class="list-item">
              <label>{{$t('插件部署方式')}}</label>
              <span>{{pluginInfo.deploy_type | filterEmpty}}</span>
            </li>
          </ul>
          <div class="list-item plugin-desc">
            <label>{{$t('插件描述')}}</label>
            <span>{{pluginInfo.scenario | filterEmpty}}</span>
          </div>
        </div>
        <div class="detail-operate">
          <template v-if="pluginInfo.is_ready">
            <bk-button text title="primary" size="small" @click="handleDeploy">
              <i class="nodeman-icon nc-deploy-2"></i>
              {{ $t('去部署') }}
            </bk-button>
            <span class="operate-menu" v-test.common="'more'" ref="moreMenu" @click="handleShowMenu">
              <i class="nodeman-icon nc-more"></i>
            </span>
          </template>
          <auth-component
            v-else
            tag="span"
            :authorized="packageOperateAuth"
            :apply-info="[authInfo]">
            <template slot-scope="{ disabled }">
              <bk-button
                v-test="'ready'"
                text
                title="primary"
                size="small"
                :disabled="disabled"
                @click="handleTogglePlugin">
                <i class="nodeman-icon nc-switchon"></i>
                {{ $t('启用插件') }}
              </bk-button>
            </template>
          </auth-component>
        </div>
      </div>
    </section>
    <section class="plugin-detail-content" v-bkloading="{ isLoading: tableLoading }">
      <div class="content-header mb10">
        <i class="nodeman-icon nc-list"></i>
        {{ $t('安装包列表') }}
      </div>
      <bk-table
        :max-height="windowHeight - 230"
        :data="tableList"
        :row-style="getRowStyle">
        <bk-table-column :label="$t('包名称')" prop="pkg_name" sortable :resizable="false" min-width="140" />
        <bk-table-column :label="$t('支持部署于')" prop="support_os_cpu" sortable :resizable="false" min-width="100" />
        <bk-table-column :label="$t('最新程序版本')" prop="version" sortable :resizable="false" min-width="100" />
        <bk-table-column :label="$t('更新时间')" prop="pkg_mtime" sortable :resizable="false" min-width="120">
          <template #default="{ row }">
            {{ row.pkg_mtime | filterTimezone }}
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('操作')" :resizable="false" width="120">
          <template #default="{ row }">
            <auth-component
              tag="span"
              :authorized="packageOperateAuth"
              :apply-info="[authInfo]">
              <template slot-scope="{ disabled }">
                <bk-button
                  v-test="'versionManage'"
                  text
                  theme="primary"
                  :disabled="disabled"
                  @click="handleShowPkgVersion(row)">
                  {{ $t('版本管理') }}
                </bk-button>
              </template>
            </auth-component>
          </template>
        </bk-table-column>
      </bk-table>
    </section>
    <bk-sideslider
      :is-show.sync="versionSlider"
      :width="1200"
      :title="$t('版本管理')"
      quick-close
      transfer>
      <div slot="content" class="p30">
        <PluginVersionTable :id="id" :os="pkOs" :cpu-arch="cpuArch" @version-change="getPluginDetailData" />
      </div>
    </bk-sideslider>
    <SelectMenu
      :show="showSelectMenu"
      :target="selectMenuTarget"
      :list="list"
      :auth-info="authInfo"
      @on-hidden="showSelectMenu = false"
      @on-select="handleMenuSelect">
    </SelectMenu>
  </div>
</template>
<script lang="ts">
import { Component, Ref, Prop, Mixins } from 'vue-property-decorator';
import PluginVersionTable from './plugin-version-table.vue';
import Upload from '@/components/common/upload.vue';
import RouterBackMixin from '@/common/router-back-mixin';
import { IPk, IPluginDetail } from '@/types/plugin/plugin-type';
import { MainStore, PluginStore } from '@/store';
import pollMixin from '@/common/poll-mixin';
import { isEmpty, download } from '@/common/util';
import SelectMenu, { IListItem } from '@/components/common/select-menu.vue';

type IDetailKey = 'name' | 'category' | 'deploy_type' | 'description' | 'scenario' | 'source_app_code'; // nodes_number

@Component({
  name: 'plugin-detail',
  components: {
    PluginVersionTable,
    Upload,
    SelectMenu,
  },
})
export default class PluginPackage extends Mixins(pollMixin, RouterBackMixin) {
  @Ref('aliasInput') private readonly aliasInput!: any;
  @Ref('moreMenu')  private readonly moreMenuRef!: HTMLElement;
  @Prop({ default: 0 }) private readonly id!: number | string;

  private pkOs = '';
  private cpuArch = '';
  private aliasEdit = false;
  private tableList: IPk[] = [];
  private versionSlider = false;
  private loading = false;
  private tableLoading = false;
  private pluginInfo: IPluginDetail = {
    id: -1,
    name: '',
    category: '',
    deploy_type: '',
    description: '',
    nodes_number: 0,
    scenario: '',
    source_app_code: '',
    plugin_packages: [],
    is_ready: false,
  };
  private downLoadJobId = -1;
  private downloadRowId = -1;
  private showSelectMenu = false;
  private selectMenuTarget: HTMLElement | null = null;

  private get windowHeight() {
    return MainStore.windowHeight;
  }
  private get packageOperateAuth() {
    return this.pluginInfo.permissions && this.pluginInfo.permissions.operate;
  }
  private get authInfo() {
    return {
      action: 'plugin_pkg_operate',
      instance_id: this.id,
      instance_name: this.pluginInfo.name,
    };
  }
  private get list(): IListItem[] {
    return [{
      id: 'stop',
      name: this.$t('停用插件'),
      authorized: this.packageOperateAuth,
    }];
  }

  private async created() {
    this.loading = true;
    await this.getPluginDetailData();
    this.loading = false;
  }

  public async getPluginDetailData() {
    return new Promise(async (resolve) => {
      const pluginInfo = await PluginStore.pluginDetail(this.id);
      this.pluginInfo = pluginInfo;
      this.tableList = pluginInfo.plugin_packages ? pluginInfo.plugin_packages.map((row: IPk) => {
        // 拆分主配置和子配置字段
        const mainConfig = row.config_templates?.find(item => item.is_main);
        row.mainConfigVersion = mainConfig?.version || '--';
        row.childConfigTemplates = row.config_templates?.filter(item => !item.is_main);
        return row;
      }) : [];
      resolve(pluginInfo);
    });
  }

  private handleShowPkgVersion(row: IPk) {
    this.pkOs = row.os;
    this.cpuArch = row.cpu_arch;
    this.versionSlider = true;
  }
  public handleEditDesc() {
    this.aliasEdit = true;
    this.$nextTick(() => {
      this.aliasInput && this.aliasInput.focus();
    });
  }
  public async handleConfirmEdit() {
    const value = this.aliasInput.curValue;
    if (value === '') return;

    this.aliasEdit = false;
    const valueTrim = value.trim();
    if (valueTrim === '' || this.pluginInfo.description === valueTrim) return;
    const message = this.verificateAlias(valueTrim);
    if (message) {
      this.$bkMessage({
        theme: 'error',
        message,
      });
      return;
    }
    this.loading = true;
    const result = await PluginStore.updatePluginAlias({ pk: this.id, params: { description: valueTrim } });
    if (result) {
      this.$bkMessage({
        theme: 'success',
        message: this.$t('修改成功'),
      });
      // 修改别名
      this.pluginInfo.description = valueTrim;
    }
    this.loading = false;
  }
  public handleCancelEdit() {
    this.aliasInput && (this.aliasInput.curValue = this.pluginInfo.description);
    this.aliasEdit = false;
  }
  public async handleDownload(row: IPk) {
    this.tableLoading = true;
    const { version, project, os, cpu_arch: cpuArch, module: rowModule } = row;
    const res = await PluginStore.pluginDownload({
      category: rowModule,
      query_params: {
        project,
        version,
        os,
        cpu_arch: cpuArch,
      },
    });
    if (!isEmpty(res.job_id) && res.job_id > -1) {
      this.downloadRowId = row.id;
      this.downLoadJobId = res.job_id;
      this.runingQueue = [res.job_id];
    } else {
      this.tableLoading = false;
    }
  }
  public async handlePollData() { // 后端暂不支持批量类型的轮询
    const res = await PluginStore.getDownloadUrl({ job_id: this.downLoadJobId });
    const tableRow = this.tableList.find(item => item.id === this.downloadRowId);
    if (res.error_message) {
      this.$bkMessage({
        theme: 'error',
        message: res.error_message,
      });
    } else if (res.download_url) {
      download((tableRow as IPk).pkg_name, res.download_url);
    }
    if (res.is_finish || res.is_failed || res.download_url) {
      this.tableLoading = false;
      this.runingQueue = [];
      this.downLoadJobId = -1;
      this.downloadRowId = -1;
    }
  }
  public verificateAlias(value: string) {
    let message;
    const valueLength = value.replace(/[\u0391-\uFFE5]/g, 'aa').length;
    if (valueLength > 40) {
      message = this.$t('长度不能大于20个中文或40个英文字母');
    }
    if (!/^(?!_)(?!.*?_$)[a-zA-Z0-9_\u4e00-\u9fa5]+$/.test(value)) {
      message = this.$t('格式不正确只能包含汉字英文数字和下划线');
    }
    return message;
  }
  public handleDeploy() {
    this.$router.push({
      name: 'chooseRule',
      params: {
        defaultPluginId: this.id,
      },
    });
  }
  private getRowStyle({ row }: { row: IPk }) {
    return row.is_ready ? {} : { color: '#C4C6CC' };
  }
  // 插件包启动和停止
  private async handleTogglePlugin() {
    this.loading = true;
    const params = {
      operation: this.pluginInfo.is_ready ? 'stop' : 'ready',
      id: [this.pluginInfo.id],
    };
    const result = await PluginStore.pluginStatusOperation(params).catch(() => false);
    if (result) {
      this.pluginInfo.is_ready = !this.pluginInfo.is_ready;
    }
    this.loading = false;
  }
  private handleShowMenu() {
    this.selectMenuTarget = this.moreMenuRef;
    this.showSelectMenu = true;
  }
  private handleMenuSelect({ id }: { id: string}) {
    if (id === 'stop') {
      this.$bkInfo({
        title: this.$t('确认要停用此插件'),
        subTitle: this.$t('插件停用后将无法再继续进行部署已部署的节点不受影响'),
        okText: this.$t('停用'),
        confirmFn: () => {
          this.handleTogglePlugin();
        },
      });
    }
  }
}
</script>

<style lang="postcss" scoped>
.plugin-detail {
  &-header {
    min-height: 126px;
    background: #f8fafd;
    .nodeman-navigation-content {
      line-height: 20px;
      display: flex;
      align-items: center;
      padding: 20px 24px;
      .content-icon {
        position: relative;
        height: 20px;
        top: -3px;
        margin-left: -7px;
        font-size: 28px;
        color: #3a84ff;
        cursor: pointer;
      }
      .content-header {
        font-size: 16px;
        color: #313238;
      }
      .content-desc {
        font-size: 14px;
        color: #313238;
      }
      .content-separator {
        padding: 0 4px;
      }
      .content-edit {
        font-size: 14px;
        color: #979ba5;
        cursor: pointer;
        margin-left: 4px;
        &:hover {
          color: #3a84ff;
        }
      }
      .description-name {
        height: 20px;
        position: relative;
        top: -2px;
        width: 180px;
      }
      .alias-edit {
        font-size: 24px;
        color: #979ba5;
        cursor: pointer;
      }
      .status-label {
        line-height: 18px;
        background: #f0f1f5;
        border-radius: 2px;
        margin-left: 6px;
        padding: 0 6px;
      }
    }
    .header-container {
      display: flex;
      justify-content: space-between;
      padding: 0 24px 0 46px;
      .detail-info-list {
        display: flex;
        flex-wrap: wrap;
      }
      .list-item {
        min-width: 220px;
        max-width: 293px;
        label {
          padding-right: 6px;
          color: #979ba5;
          &::after {
            content: ":";
            position: relative;
            left: 2px;
          }
        }
        &.plugin-desc {
          max-width: none;
          margin-top: 14px;
        }
      }
      .detail-operate {
        flex-shrink: 0;
        display: flex;
        .operate-menu {
          font-size: 14px;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          color: #979ba5;
          &:hover {
            background: #ddd;
            color: #3a84ff;
          }
        }
        i {
          font-size: 14px;
        }
      }
    }
  }
  &-content {
    padding: 20px 24px;
    .content-header {
      color: #313238;
      font-size: 14px;
      display: flex;
      align-items: center;
      i {
        color: #979ba5;
        margin-right: 6px;
      }
    }
    .text-btn {
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
      width: 100%;
      text-align: left;
      >>> & > div {
        display: inline-block;
      }
    }
    .config-cell {
      .config-list {
        display: inline-block;
        padding: 10px 0;
        line-height: 20px;
        max-width: 100%;
      }
      .config-item {
        display: flex;
        width: 100%;
      }
      .config-item-name {
        flex: 1;
        display: inline-block;
        height: 20px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap
      }
    }
  }
}
</style>
