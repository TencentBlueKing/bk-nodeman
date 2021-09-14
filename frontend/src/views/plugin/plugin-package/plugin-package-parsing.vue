<template>
  <div class="plugin-package-parsing" v-bkloading="{ isLoading: loading }">
    <div class="plugin-package-status">
      <i18n path="插件包已选个数" class="title">
        <span>{{ selectedNum }}</span>
      </i18n>
      <div class="count">
        <span v-for="(item, index) in statusList" :key="item.status">
          <i18n :path="item.path">
            <span :class="item.status">{{ item.count }}</span>
          </i18n>
          <span class="separator" v-if="index !== (statusList.length - 1)">, </span>
        </span>
      </div>
    </div>
    <bk-table
      :data="tableList"
      class="package-parsing-table mb30"
      :max-height="windowHeight - 220"
      @select="handleSelect"
      @select-all="handleSelect">
      <bk-table-column type="selection" width="60" :selectable="handleSelectable" />
      <bk-table-column :label="$t('包名称')" prop="pkg_name" sortable show-overflow-tooltip />
      <bk-table-column :label="$t('插件名称')" prop="project" sortable show-overflow-tooltip />
      <bk-table-column :label="$t('开发商')" prop="category" sortable :resizable="false" />
      <bk-table-column :label="$t('主程序版本')" prop="version" sortable :resizable="false" />
      <bk-table-column :label="$t('主配置版本')" prop="mainConfigVersion" :resizable="false" />
      <bk-table-column :label="$t('子配置版本')" class-name="config-cell">
        <template #default="{ row }">
          <ul class="config-list" v-if="row.childConfigTemplates && row.childConfigTemplates.length">
            <li
              class="config-item"
              v-for="(config, index) in row.childConfigTemplates"
              :key="index"
              :title="config.name">
              <span class="config-item-name">{{ config.name }}</span>
              <span class="ml10 config-item-version">{{ config.version }}</span>
            </li>
          </ul>
          <span v-else>--</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('支持系统')" prop="cpu_arch" :resizable="false" />
      <bk-table-column :label="$t('插件描述')" prop="description" :resizable="false" />
      <bk-table-column :label="$t('解析结果')" prop="message" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="col-execution">
            <span :class="`execut-mark execut-${ row.result ? 'success' : 'failed' }`"></span>
            <span class="execut-text" :title="row.parseRes">{{ row.message | filterEmpty }}</span>
          </div>
        </template>
      </bk-table-column>
    </bk-table>
    <div class="package-parsing-footer">
      <auth-component
        tag="div"
        ext-cls="mr10"
        :authorized="authority.import_action"
        :apply-info="[{ action: 'plugin_pkg_import' }]">
        <template slot-scope="{ disabled }">
          <bk-button
            v-test.common="'formCommit'"
            theme="primary"
            ext-cls="import-btn"
            :loading="loadingSetupBtn"
            :disabled="disabled || !selectedNum || loadingSetupBtn"
            @click="handleImport">
            <div class="import">
              <span>{{ $t('导入') }}</span>
              <span class="num">{{ selectedNum }}</span>
            </div>
          </bk-button>
        </template>
      </auth-component>
      <bk-button class="nodeman-cancel-btn" @click="handleCancel">{{ $t('取消') }}</bk-button>
    </div>
  </div>
</template>
<script lang="ts">
import { Mixins, Component, Prop } from 'vue-property-decorator';
import PluginPackageTable from './plugin-package-table.vue';
import { MainStore, PluginStore } from '@/store';
import pollMixin from '@/common/poll-mixin';
import { IPkParseRow } from '@/types/plugin/plugin-type';

@Component({
  name: 'plugin-package-parsing',
  components: {
    PluginPackageTable,
  },
})
export default class PluginPackage extends Mixins(pollMixin) {
  @Prop({ default: '' }) private readonly filename!: string;
  @Prop({ default: '' }) private readonly packageName!: string;

  private loading = false;
  private loadingSetupBtn = false;
  private searchValue = '';
  private tableList: IPkParseRow[] = [];
  private selectList: IPkParseRow[] = [];
  private statusConut = {
    success: 0,
    failed: 0,
  };

  private get statusList() {
    const statusMap = {
      success: '解析通过个数',
      failed: '解析失败个数',
    };
    const data = (Object.keys(this.statusConut) as Array<keyof typeof statusMap>).map(key => ({
      path: statusMap[key],
      count: this.statusConut[key],
      status: key,
    }));
    return data.filter(item => !!item.count);
  }
  private get selectedNum() {
    return this.selectList.length;
  }
  private get windowHeight() {
    return MainStore.windowHeight;
  }
  private get authority() {
    return PluginStore.authorityMap;
  }

  private created() {
    this.handleGetParseData();
  }

  public async handleGetParseData() {
    this.loading = true;
    const params = this.packageName ? {
      file_name: this.filename,
      is_update: true,
      project: this.packageName,
    } : {
      file_name: this.filename,
    };
    const data = await PluginStore.packageParse(params);
    this.statusConut = {
      success: 0,
      failed: 0,
    };
    this.tableList = data.map((row) => {
      // 拆分主配置和子配置字段
      const mainConfig = row.config_templates?.find(item => item.is_main);
      row.mainConfigVersion = mainConfig?.version;
      row.childConfigTemplates = row.config_templates?.filter(item => !item.is_main);
      // 统计成功和失败状态
      if (row.result) {
        this.statusConut.success += 1;
      } else {
        this.statusConut.failed += 1;
      }
      return row;
    });
    this.loading = false;
  }

  public handleSelectable(row: IPkParseRow) {
    return row.result;
  }

  public handleSelect(selection: IPkParseRow[]) {
    this.selectList = selection;
  }
  public async handleImport() {
    this.loadingSetupBtn = true;
    const params = {
      file_name: this.filename,
      is_release: true,
      is_template_load: true,
      is_template_overwrite: true,
      select_pkg_abs_paths: this.selectList.map(item => item.pkg_abs_path),
    };
    const res = await PluginStore.pluginPkgImport(params);
    if (res.job_id) {
      this.runingQueue.push(res.job_id);
    } else {
      this.loadingSetupBtn = false;
    }
  }
  // 轮询插件注册任务状态
  public async handlePollData() { // 后端暂不支持批量类型的轮询
    const jobId = this.runingQueue.join('');
    const res = await PluginStore.getRegisterTask({ job_id: jobId });
    const status = (res.status || '').toLowerCase();
    if (status === 'success' || status === 'failed') {
      this.loadingSetupBtn = false;
      this.runingQueue = [];
      if (status === 'success') {
        this.$router.push({
          name: 'pluginPackage',
        });
      } else if (status === 'failed' && res.message) {
        this.$bkMessage({
          theme: 'error',
          message: res.message,
        });
      }
    }
  }
  public handleCancel() {
    this.$router.replace({ name: 'pluginPackage' });
  }
}
</script>

<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

.package-top {
  display: flex;
  justify-content: space-between;
}
.package-import-btn {
  min-width: 104px;
}
.package-search-input {
  width: 500px;
}
.plugin-package-table {
  margin-top: 14px;
}
>>> .plugin-import-dialog {
  /* stylelint-disable-next-line declaration-no-important */
  z-index: 50!important;
}
.plugin-package-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 42px;
  background: #f0f1f5;
  border: 1px solid #dcdee5;
  border-bottom: 0;
  padding: 0 22px;
  .title {
    font-weight: 700;
  }
  .success {
    color: #2dcb56;
    font-weight: 700;
  }
  .failed {
    color: #ea3636;
    font-weight: 700;
  }
}
.plugin-import-content {
  background: #fff;
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
.package-parsing-footer {
  @mixin layout-flex row, center, center;
  .import-btn {
    min-width: 120px;
    &.is-disabled .num {
      color: #dcdee5;
      background: #fff;
    }
  }
  .import {
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
</style>
