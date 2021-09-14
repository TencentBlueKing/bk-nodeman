<template>
  <article class="agent-setup" v-bkloading="{ isLoading: loading }">
    <!--左侧表单信息-->
    <section class="agent-setup-left" ref="setupContent">
      <tips class="mb20">
        <template #default>
          <ul>
            <li v-if="!showSetupBtn" class="tips-content-item">{{ importTips }}</li>
            <li class="tips-content-item" v-if="showSetupBtn">
              {{ $t('安装要求tips', { type: 'Agent' }) }}
              <bk-link class="tips-link" theme="primary" @click="handleShowPanel">{{ $t('安装要求') }}</bk-link>
              {{ $t('表格展示设置tips') }}
              <bk-link class="tips-link" theme="primary" @click="handleShowSetting">{{ $t('表格展示设置') }}</bk-link>
            </li>
          </ul>
        </template>
      </tips>
      <FilterIpTips
        class="mb15"
        v-if="filterList.length && showFilterTips"
        @click="handleShowDetail">
      </FilterIpTips>
      <bk-form
        ref="form"
        v-if="showTab"
        class="mb20 fs0 label-tl-form auto-width-form"
        :label-width="0">
        <install-method required :is-manual="isManual" @change="installMethodHandle"></install-method>
      </bk-form>
      <bk-form form-type="vertical" v-test.agentImport="'importForm'">
        <bk-form-item :class="{ 'form-item-not-lable': !showTab }" :label="$t('安装信息')" required>
          <InstallTable
            ref="setupTable"
            :local-mark="`agent${isManual ? '_manual' : '' }_${type}`"
            :setup-info="setupInfo"
            :is-manual="isManual"
            :min-items="minItems"
            :height="scrollHeight"
            :need-plus="false"
            :virtual-scroll="virtualScroll"
            :extra-params="extraParams"
            auto-sort
            @delete="handleItemDelete">
            <template #empty>
              <parser-excel v-model="importDialog" @uploading="handleUploading"></parser-excel>
            </template>
          </InstallTable>
        </bk-form-item>
      </bk-form>
      <div class="mt30 left-footer">
        <bk-button
          v-if="!showSetupBtn"
          theme="primary"
          ext-cls="nodeman-primary-btn mr10"
          v-test="'formImport'"
          :disabled="disabledImport"
          :loading="isUploading"
          @click="handleImport">
          {{ $t('导入') }}
        </bk-button>
        <div class="btn-wrapper" v-else>
          <bk-button
            theme="primary"
            ext-cls="nodeman-primary-btn mr10"
            v-test.common="'formCommit'"
            :loading="loadingSetupBtn"
            @click="handleSetup">
            <div class="install">
              <span>{{ setupBtnText }}</span>
              <span class="num">{{ setupNum }}</span>
            </div>
          </bk-button>
          <bk-button
            class="nodeman-cancel-btn mr10"
            v-if="!isEdit"
            @click="handleLastStep">
            {{ $t('上一步') }}
          </bk-button>
        </div>
        <bk-button class="nodeman-cancel-btn" @click="handleCancel">{{ $t('取消') }}</bk-button>
      </div>
    </section>
    <!--右侧提示信息-->
    <section class="agent-setup-right" :class="{ 'right-panel': showRightPanel }">
      <RightPanel v-model="showRightPanel" :host-type="hostType" :host-list="hostList"></RightPanel>
    </section>
    <!--过滤ip信息-->
    <FilterDialog v-model="showFilterDialog" :list="filterList" :title="$t('忽略详情')"></FilterDialog>
  </article>
</template>
<script lang="ts">
import { Component, Ref, Mixins, Prop } from 'vue-property-decorator';
import { MainStore, AgentStore, CloudStore } from '@/store/index';
import RightPanel from '@/components/common/right-panel-tips.vue';
import InstallTable from '@/components/setup-table/install-table.vue';
import InstallMethod from '@/components/common/install-method.vue';
import Tips from '@/components/common/tips.vue';
import FilterIpTips from '@/components/common/filter-ip-tips.vue';
import mixin from '@/components/common/filter-ip-mixin';
import FilterDialog from '@/components/common/filter-dialog.vue';
import ParserExcel from '../components/parser-excel.vue';
// import getTipsTemplate from '../config/tips-template'
import { tableConfig, tableManualConfig } from '../config/importTableConfig';
import { editConfig, editManualConfig } from '../config/editTableConfig';
import { addListener, removeListener } from 'resize-detector';
import { debounce, deepClone, isEmpty } from '@/common/util';
import { IAgent, IAgentHost, IAgentSearch } from '@/types/agent/agent-type';
import { IApExpand } from '@/types/config/config';
import { ISetupHead, ISetupRow } from '@/types';

@Component({
  name: 'agent-import',
  components: {
    RightPanel,
    InstallTable,
    InstallMethod,
    ParserExcel,
    FilterDialog,
    Tips,
    FilterIpTips,
  },
})

export default class AgentImport extends Mixins(mixin) {
  @Prop({
    type: Array,
    default: () => [],
  }) private readonly tableData!: IAgentHost[];
  // 是否是跨页全选（true时：tableData为标记删除的数据  false时：tableData为当前要编辑的数据）
  @Prop({ type: Boolean, default: false }) private readonly isSelectedAllPages!: boolean;
  // 标记删除法的查询条件
  @Prop({ type: Object, default: () => ({}) }) private readonly condition!: IAgentSearch;
  @Prop({
    type: String,
    default: 'INSTALL_AGENT',
    validator(v) {
      return ['INSTALL_AGENT', 'REINSTALL_AGENT', 'RELOAD_AGENT', 'UPGRADE_AGENT', 'UNINSTALL_AGENT'].includes(v);
    },
  }) private readonly type!: string;
  @Ref('setupContent') private readonly setupContent!: Element;
  @Ref('setupTable') private readonly setupTable!: any;

  private isManual = false;
  // Excel 导入提示
  private importTips = this.$t('excel导入提示');
  // 右侧提示面板是否显示
  private showRightPanel = false;
  // 总的数据备份，包括Excel导入数据
  private tableDataBackup: ISetupRow[] = [];
  // agent安装信息表格
  private setupInfo: { header: ISetupHead[], data: ISetupRow[] } = {
    header: tableConfig,
    data: [],
  };
  // 监听界面滚动
  private listenResize: any = null;
  private isScroll = false;
  // 导入对话框
  private importDialog = false;
  // 导入按钮加载状态
  private isUploading = false;
  // 安装按钮加载状态
  private loadingSetupBtn = false;
  // 是否显示安装按钮
  private showSetupBtn = false;
  private height = 0;
  // 安装信息加载状态
  private loading = false;
  // 编辑head
  private editTableHead: { editConfig: ISetupHead[], editManualConfig: ISetupHead[]  } = {
    editConfig: [],
    editManualConfig: [],
  };

  // 导入按钮禁用状态
  private get disabledImport() {
    return !this.setupInfo.data.length;
  }
  private get setupNum() {
    return this.setupInfo.data.length;
  }
  // 是否支持虚拟滚动
  private get virtualScroll() {
    // 44 : 表格一行的高度
    return this.setupNum * 44 >= (this.height - this.surplusHeight);
  }
  // 虚拟滚动高度
  private get scrollHeight() {
    // 135： footer、表头和tips的高度
    return this.virtualScroll && this.height ? `${this.height - this.surplusHeight}px` : 'auto';
  }
  private get isInstallType() {
    return ['INSTALL_AGENT', 'REINSTALL_AGENT'].includes(this.type);
  }
  // 剩余高度
  private get surplusHeight() {
    let height = 135; // 以下条件可能并列出现
    // tips的行高
    height += 37;
    // 全部过滤提示的行高
    if (this.filterList.length && this.showFilterTips) {
      height += 52;
    }
    // 安装类型的行高
    if (this.showSetupBtn && this.isInstallType) {
      height += 94;
    }
    return height;
  }
  // 是否是编辑态
  private get isEdit() {
    return !!(this.tableData && this.tableData.length) || this.isSelectedAllPages;
  }
  private get isNotAutoSelect() {
    return AgentStore.apList.length === 1;
  }
  // 最小安装信息数目
  private get minItems() {
    if (this.isEdit) return 1;
    return 0;
  }
  // 安装按钮文案
  private get setupBtnText() {
    const textMap: IAgent = {
      INSTALL_AGENT: this.$t('安装'),
      REINSTALL_AGENT: this.$t('重装'),
      RELOAD_AGENT: this.$t('重载配置'),
      UPGRADE_AGENT: this.$t('升级'),
      UNINSTALL_AGENT: this.$t('卸载'),
    };
    return textMap[this.type];
  }
  // 编辑态额外参数
  private get extraParams() {
    if (this.isEdit) return ['bk_host_id', 'is_manual'];
    return ['outer_ip', 'is_manual'];
  }
  // 右侧面板提示类型
  private get hostType() {
    const isAgent = this.setupInfo.data.every(item => item
        && item.bk_cloud_id === window.PROJECT_CONFIG.DEFAULT_CLOUD);
    const isPagent = this.setupInfo.data.every(item => item
        && item.bk_cloud_id !== window.PROJECT_CONFIG.DEFAULT_CLOUD);
    if (isAgent) {
      return 'Agent';
    } if (isPagent) {
      return 'Pagent';
    }
    return 'mixed';
  }
  private get hostList() {
    const list = this.setupInfo.data.map((item) => {
      if (!item) {
        return {};
      }
      const cloudFind = AgentStore.cloudList.find(cloud => item.bk_cloud_id === cloud.bk_cloud_id);
      return {
        bk_cloud_id: item.bk_cloud_id,
        bk_cloud_name: cloudFind ? cloudFind.bk_cloud_name : '',
        inner_ip: item.inner_ip,
        ap_id: item.ap_id,
      };
    });
    list.sort((a, b) => (a.bk_cloud_id as number) - (b.bk_cloud_id as number));
    return list;
  }
  private get showTab() {
    return this.showSetupBtn && ['INSTALL_AGENT', 'REINSTALL_AGENT'].includes(this.type);
  }

  private created() {
    switch (this.type) {
      case 'REINSTALL_AGENT':
        MainStore.setNavTitle(window.i18n.t('重装Agent'));
        break;
      case 'RELOAD_AGENT':
        MainStore.setNavTitle(window.i18n.t('重载Agent配置'));
        break;
    }
    this.resetTableHead();
  }
  private mounted() {
    this.handleInit();
    this.listenResize = debounce(300, () => this.handleResize());
    addListener(this.$el as HTMLElement, this.listenResize);
    this.height = this.setupContent.clientHeight;
  }
  private beforeDestroy() {
    AgentStore.setApUrl({ id: '', urlType: '' });
    removeListener(this.$el as HTMLElement, this.listenResize);
  }

  private async handleInit() {
    this.loading = true;
    const promiseList = [];
    // ieod 环境：excel 导入去掉直连区域，编辑操作正常回写
    promiseList.push(AgentStore.getCloudList(this.isEdit ? {} : { RUN_VER: window.PROJECT_CONFIG.RUN_VER }));
    promiseList.push(AgentStore.getApList(!this.isEdit).then((res) => {
      AgentStore.setApUrl({ id: -1, urlType: '' });
      return res;
    }));
    promiseList.push(CloudStore.getChannelList());
    // if (!this.bkBizList.length) {
    //   promiseList.push(this.getBkBizList({ action: 'agent_view' }))
    // }
    await Promise.all(promiseList);
    if (this.isEdit) {
      await this.handleInitEditData();
    }
    this.$nextTick().then(() => {
      this.loading = false;
    });
  }
  /**
     * 初始化编辑态数据
     */
  private async handleInitEditData() {
    this.showSetupBtn = true;
    let data: ISetupRow[] = [];
    const apDefault = this.isNotAutoSelect ? AgentStore.apList[0].id : '';
    if (this.isSelectedAllPages) {
      const res = await AgentStore.getHostList(this.condition);
      data = res.list.map((item: IAgentHost) => {
        const ap = this.isNotAutoSelect && item.ap_id === -1
          ? { ap_id: apDefault }
          : {};
          // 打平数据
        return Object.assign({}, item, item.identity_info, ap);
      });
    } else {
      data = JSON.parse(JSON.stringify(this.isNotAutoSelect
        ? this.tableData.map(item => (item.ap_id === -1 ? Object.assign(item, { ap_id: apDefault }) : item))
        : this.tableData));
    }
    // 将原始的数据备份；切换安装方式时，接入点的数据变更后的回退操作时需要用到
    this.tableDataBackup = data;
    this.setupInfo.data = deepClone(data);
    this.isManual = this.showTab
      ? data.every((item: ISetupRow) => item.is_manual) : data.some((item: ISetupRow) => item.is_manual);
    // 编辑态安装信息表格配置
    this.setupInfo.header = this.isManual ? this.editTableHead.editManualConfig : this.editTableHead.editConfig;
    this.setupTable.handleInit();
    this.setupTable.handleScroll();
  }
  /**
   * 监听界面滚动
   */
  private handleResize() {
    // 60：三级导航的高度  52： 一级导航高度
    this.isScroll = this.$el.scrollHeight + 60 > this.$root.$el.clientHeight - 52;
  }
  /**
     * 导入excel对话框
     */
  private handleShowDialog() {
    this.importDialog = true;
  }
  /**
     * 导入按钮点击事件
     */
  private handleImport() {
    this.setupTable.handleInit();
    this.setupTable.handleScroll();
    this.showSetupBtn = true;
  }
  /**
   * 安装操作
   */
  private async handleSetup() {
    const setupTableValidate = this.setupTable.validate();
    if (setupTableValidate) {
      this.loadingSetupBtn = true;
      let hosts = this.setupTable.getData();
      hosts.forEach((item: ISetupRow) => {
        if (isEmpty(item.login_ip)) {
          delete item.login_ip;
        }
        if (isEmpty(item.bt_speed_limit)) {
          delete item.bt_speed_limit;
        } else {
          item.bt_speed_limit = Number(item.bt_speed_limit);
        }
        item.peer_exchange_switch_for_agent = Number(item.peer_exchange_switch_for_agent);
        if (item.install_channel_id === 'default') {
          item.install_channel_id = null;
        }
      });
      // 安装agent或pagent时，需要设置初始的安装类型
      if (['INSTALL_AGENT', 'REINSTALL_AGENT'].includes(this.type)) {
        const isManual = { is_manual: this.isManual };
        hosts = hosts.map((item: ISetupRow) => Object.assign(item, isManual));
      }
      const params = {
        job_type: this.type,
        hosts,
      };
      const res = await AgentStore.installAgentJob({
        params,
        config: {
          needRes: true,
          globalError: false,
        },
      });
      this.loadingSetupBtn = false;
      if (!res) return;

      if (res.result || res.code === 3801018) {
        // mixin: handleFilterIp 处理过滤IP信息
        this.handleFilterIp(res.data, this.type === 'INSTALL_AGENT');
      } else if (res.code === 3801013) {
        // Proxy过期或者未安装
        const data = this.setupTable.getTableData().map((item: ISetupRow) => {
          const filterProxy = res.data.ip_filter.find((obj: any) => {
            const objId = `${obj.ip}${obj.bk_cloud_id}`;
            const itemId = `${item.inner_ip}${item.bk_cloud_id}`;
            return objId === itemId;
          });
          if (filterProxy) {
            item.proxyStatus = filterProxy.exception;
          }
          return item;
        });
        this.setupTable.handleUpdateData(data);
        this.setupTable.validate(); // 重新排序
      } else {
        const message = res.message ? res.message : this.$t('请求出错');
        this.$bkMessage({
          message,
          delay: 3000,
          theme: 'error',
        });
      }
    }
  }
  /**
     * 上一步
     */
  private handleLastStep() {
    this.showFilterTips = false;
    this.filterList.splice(0, this.filterList.length);
    this.setupInfo.data.splice(0, this.setupInfo.data.length);
    this.tableDataBackup.splice(0, this.tableDataBackup.length);
    this.showSetupBtn = false;
    this.setupTable.handleInit();
    this.setupTable.handleScroll();
  }
  /**
     * 取消安装Agent
     */
  private handleCancel() {
    this.$router.push({ name: 'agentStatus' });
  }
  /**
     * 处理文件上传状态
     * @param {Boolean} loading true: 正在解析 false：解析完毕
     * @param {Array} v 解析数据
     */
  private handleUploading(loading: boolean, v: ISetupRow[]) {
    this.isUploading = loading;
    if (!this.isUploading && v && v.length) {
      this.tableDataBackup = v;
      this.setupInfo.data = deepClone(v);
    }
  }
  /**
     * 删除item
     */
  private handleItemDelete(index: number) {
    this.setupInfo.data.splice(index, 1);
    this.tableDataBackup.splice(index, 1);
    if (!this.setupInfo.data.length) {
      this.handleLastStep();
    }
  }
  /**
   * 安装方式切换
   */
  private installMethodHandle(isManual = false) {
    this.isManual = isManual;
    // const data: ISetupRow[] = deepClone(this.setupTable.getData())
    const data: ISetupRow[] = deepClone(this.tableDataBackup);
    let apList: IApExpand[] = deepClone(AgentStore.apList);
    if (this.isManual) {
      this.setupInfo.header = this.isEdit ? editManualConfig : tableManualConfig;
      // 手动安装无自动选择
      apList = apList.filter(item => item.id !== -1);
      // 自动接入点改默认接入点
      const apDefault = this.isNotAutoSelect
        ? AgentStore.apList[0]
        : AgentStore.apList.find(item => item.is_default);
      const apDefaultId = apDefault ? apDefault.id : '';
      // 将自动选择的行 替换为默认接入点
      data.forEach((item) => {
        if (item.ap_id === -1) {
          item.ap_id = apDefaultId as number;
        }
      });
    } else {
      if (!apList.find(item => item.id === -1)) {
        const obj = {
          id: -1,
          name: this.$t('自动选择'),
        };
        apList.unshift(obj as IApExpand);
      }
      this.setupInfo.header = this.isEdit ? editConfig : tableConfig;
      data.forEach((item, index: number) => {
        item.ap_id = this.tableDataBackup[index].ap_id;
      });
    }
    AgentStore.setApList(apList);
    this.setupInfo.data = data;
    this.setupTable.handleInit();
    this.setupTable.handleScroll();
  }
  private handleShowSetting() {
    this.setupTable.handleToggleSetting(true);
  }
  private resetTableHead() {
    if (this.type === 'RELOAD_AGENT') {
      const reload = [
        'inner_ip',
        'bk_biz_id',
        'bk_cloud_id',
        'ap_id',
        'os_type',
        'peer_exchange_switch_for_agent',
        'bt_speed_limit',
      ];
      this.editTableHead.editConfig = editConfig.filter(item => reload.includes(item.prop) || item.type === 'operate')
        .map(item => Object.assign({ ...item }, { show: true }));
      this.editTableHead.editManualConfig = editManualConfig.map(item => Object.assign({ ...item }, { show: true }));
    } else {
      this.editTableHead.editConfig = editConfig;
      this.editTableHead.editManualConfig = editManualConfig;
    }
  }
  private handleShowPanel() {
    this.setupInfo.data = deepClone(this.setupTable.getData());
    this.showRightPanel = true;
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

.agent-setup {
  @mixin layout-flex row;
  &-left {
    flex: 1;
    height: calc(100vh - 120px);
    .left-footer {
      @mixin layout-flex row, center, center;
      .btn-wrapper {
        @mixin layout-flex row;
      }
      .install {
        @mixin layout-flex row, center, center;
        .num {
          margin-left: 8px;
          padding: 0 6px;
          height: 16px;
          border-radius: 8px;
          background: #e1ecff;
          color: #3a84ff;
          font-weight: bold;
          font-size: 12px;

          @mixin layout-flex row, center, center;
        }
      }
    }
  }
}
</style>
