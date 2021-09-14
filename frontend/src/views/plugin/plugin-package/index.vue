<template>
  <div class="plugin-package" v-test="'package'">
    <div class="package-top">
      <auth-component
        tag="div"
        :authorized="authority.import_action"
        :apply-info="[{ action: 'plugin_pkg_import' }]">
        <template slot-scope="{ disabled }">
          <bk-button
            class="package-import-btn"
            v-test="'import'"
            theme="primary"
            :disabled="disabled"
            @click="handleImport">
            {{ $t('导入插件') }}
          </bk-button>
        </template>
      </auth-component>
      <bk-input
        v-test="'search'"
        :placeholder="$t('搜索插件别名插件名称')"
        right-icon="bk-icon icon-search"
        ext-cls="package-search-input"
        clearable
        v-model.trim="searchValue"
        @change="handleValueChange">
      </bk-input>
    </div>
    <PluginPackageTable
      class="plugin-package-table"
      :table-list="tableList"
      :pagination="pagination"
      :num-loading="numLoading"
      v-bkloading="{ isLoading }"
      @page-change="handlePageChange"
      @limit-change="handleLimitChange">
    </PluginPackageTable>
    <bk-dialog
      width="480"
      ext-cls="plugin-import-dialog"
      :mask-close="false"
      :header-position="'left'"
      :title="importTitle"
      :value="showUploadDialog"
      @cancel="onCloseDialog">
      <div class="plugin-import-content">
        <Upload
          v-if="showUploadDialog"
          name="package_file"
          accept="application/x-compressed,application/x-gzip,application/gzip"
          :action="`${baseUrl}v2/plugin/upload/`"
          :headers="uploadHeader"
          :on-upload-success="handleUploadSuccess"
          :on-upload-error="handleUploadError"
          :on-upload-progress="handleUploadProgress">
        </Upload>
      </div>
      <div class="plugin-import-footer" slot="footer">
        <div class="button-group">
          <bk-button
            v-test.common="'formCommit'"
            theme="primary"
            :disabled="!uploadFileName || uploadLoading"
            :loading="uploadLoading"
            @click="handleDialogStep">
            {{ $t('下一步') }}
          </bk-button>
          <bk-button
            theme="default"
            class="ml5"
            @click="onCloseDialog">
            {{ $t('取消') }}
          </bk-button>
        </div>
      </div>
    </bk-dialog>
  </div>
</template>
<script lang="ts">
import cookie from 'cookie';
import { Vue, Component } from 'vue-property-decorator';
import PluginPackageTable from './plugin-package-table.vue';
import Upload from '@/components/common/upload.vue';
import { PluginStore } from '@/store';
import { debounceDecorate } from '@/common/util';
import { IPluginRow } from '@/types/plugin/plugin-type';
import { IPagination } from '@/types';

@Component({
  name: 'plugin-package',
  components: {
    PluginPackageTable,
    Upload,
  },
})
export default class PluginPackage extends Vue {
  private searchValue = '';
  private tableList: IPluginRow[] = [];
  private showUploadDialog = false;
  private isLoading = false;
  private numLoading = false;
  private uploadLoading = false;
  private uploadFileName = '';
  private uploadPackageName = '';
  private uploadHeader = [
    { name: 'X-REQUESTED-WITH', value: 'XMLHttpRequest' },
    { name: 'X-CSRFToken', value: cookie.parse(document.cookie)[`${window.PROJECT_CONFIG.APP_CODE}_csrftoken`] },
  ];
  private pagination: IPagination = {
    current: 1,
    count: 0,
    limit: 50,
    limitList: [50, 100, 200],
  };
  private baseUrl = `${window.PROJECT_CONFIG.SITE_URL}${AJAX_URL_PREFIX}`;

  private get importTitle() {
    return this.uploadPackageName ? `${this.$t('更新插件包')}: ${this.uploadPackageName}` : this.$t('导入插件');
  }
  private get authority() {
    return PluginStore.authorityMap;
  }

  private created() {
    this.getPkgList();
  }

  public async getPkgList() {
    this.isLoading = true;
    this.numLoading = true;
    const { current, limit } = this.pagination;
    const params = {
      search: this.searchValue,
      page: current,
      pagesize: limit,
    };
    const { total, list } = await PluginStore.pluginPkgList(params);
    this.pagination.count = total;
    this.tableList = list;
    this.isLoading = false;
    this.getTableNodeNum();
  }
  @debounceDecorate(700)
  public handleValueChange() {
    this.getPkgList();
  }
  public async getTableNodeNum() {
    this.numLoading = true;
    const plugins: string[] = this.tableList.map(row => row.name);
    if (plugins.length) {
      const numMap = await PluginStore.pluginPkgNodeNum({ projects: plugins });
      this.tableList.forEach((row) => {
        if (numMap[row.name]) {
          row.nodes_number = numMap[row.name].nodes_number;
        }
      });
    }
    this.numLoading = false;
  }
  public handleImport(row: IPluginRow) {
    if (row) {
      this.uploadPackageName = row.name;
    }
    this.showUploadDialog = true;
  }
  public handleDialogStep() {
    this.$router.push({
      name: 'pluginPackageParse',
      params: {
        filename: this.uploadFileName,
        packageName: this.uploadPackageName,
      },
    });
  }
  public onCloseDialog() {
    this.uploadFileName = '';
    this.uploadPackageName = '';
    this.showUploadDialog = false;
  }
  public handlePageChange(page: number) {
    this.pagination.current = page;
    this.handleValueChange();
  }
  public handleLimitChange(limit: number) {
    this.pagination.limit = limit;
    this.handleValueChange();
  }
  public handleUploadSuccess(res: { result?: boolean, data: { name: string } }) {
    this.uploadLoading = false;
    if (res.result) {
      this.uploadFileName = res.data.name;
    }
  }
  public handleUploadError() {
    this.uploadLoading = false;
  }
  public handleUploadProgress() {
    this.uploadLoading = true;
  }
}
</script>

<style lang="postcss" scoped>
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
  .plugin-import-content {
    font-size: 12px;
  }
</style>
