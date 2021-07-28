<template>
  <div class="agent-version-detail">
    <div class="table-header">
      <div class="table-header-left">
        <span class="package-name">{{ $t('Agent包', { name: name }) }}</span>
        <i18n path="已选条数" class="package-selection">
          <span class="selection-num">{{ selection }}</span>
        </i18n>
      </div>
      <div class="table-header-right">
        <span v-if="table.statistics.success">
          <span class="status-success">{{ table.statistics.success }}</span>
          {{ $t('检测成功') }}
        </span>
        <span class="separator" v-if="table.statistics.success && table.statistics.error">,</span>
        <span v-if="table.statistics.error">
          <span class="status-error">{{ table.statistics.error }}</span>
          {{ $t('检测失败') }}
        </span>
      </div>
    </div>
    <bk-table :data="table.data" @selection-change="handleSelectionChange">
      <bk-table-column type="expand" width="60" align="center">
        <template #default="{ row }">
          <div class="detail-content">
            <div class="detail-row">
              <div class="detail-row-cell">
                <label>{{ $t('操作系统') }}:</label>
                {{ row.os_type }}
              </div>
              <div class="detail-row-cell">
                <label>{{ $t('版本号') }}:</label>
                {{ row.version }}
              </div>
              <div class="detail-row-cell">
                <label>{{ $t('MD5') }}:</label>
                {{ row.md5 }}
              </div>
            </div>
            <div class="detail-row mt15">
              <div class="detail-row-cell file">
                <label>{{ $t('文件列表') }}:</label>
                <ul class="file-list">
                  <li v-for="(item, index) in row.file_list" :key="index">
                    {{ item }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column type="selection" width="26" :selectable="handleSelectable"></bk-table-column>
      <bk-table-column :label="$t('操作系统')" prop="os_type" width="280"></bk-table-column>
      <bk-table-column :label="$t('版本号')" prop="version" width="280"></bk-table-column>
      <bk-table-column :label="$t('检测结果')" prop="status" width="280">
        <template #default="{ row }">
          <span v-if="row.status" class="status-success">{{ $t('检测成功') }}</span>
          <span v-else class="status-error">{{ $t('检测失败') }}</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('失败原因')" prop="msg">
        <template #default="{ row }">
          <span v-if="row.msg" class="status-error">{{ row.msg }}</span>
          <span v-else>--</span>
        </template>
      </bk-table-column>
    </bk-table>
    <div class="footer mt30">
      <bk-button
        theme="primary"
        :loading="importLoading"
        :disabled="importDisabled"
        ext-cls="nodeman-primary-btn mr10"
        @click="handleImport">
        {{ $t('导入') }}
      </bk-button>
      <bk-button ext-cls="nodeman-cancel-btn mr10" @click="handleLastStep">{{ $t('上一步') }}</bk-button>
      <bk-button ext-cls="nodeman-cancel-btn" @click="handleCancel">{{ $t('取消') }}</bk-button>
    </div>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { IAgentHost } from '@/types/agent/agent-type';

@Component({ name: 'agent-version-detail' })

export default class AgentVersionDetail extends Vue {
  @Prop({ type: String, default: '文件名' }) private readonly name!: string;


  private table = {
    data: [
      {
        os_type: 'Linux',
        version: '1.1.1',
        status: 0,
        msg: 'result_msg',
        md5: 'sabbsabbdsab2w12',
        file_list: [
          'gse/agent_linux_x86/bin/gse_agentgse/agent_linux_x86/bin/gse_agentgse/agent_linux_x86/bin/gse_agent',
          'gse/agent_linux_x86/bin/gse_agent',
          'gse/agent_linux_x86/bin/gse_agent',
          'gse/agent_linux_x86/bin/gse_agent',
        ],
      },
      {
        os_type: 'MacOs',
        version: '6.1.1',
        status: 1,
        msg: '',
        md5: 'sabbsabbdsab2w12',
        file_list: [
          'gse/agent_linux_x86/bin/gse_agent',
          'gse/agent_linux_x86/bin/gse_agent',
          'gse/agent_linux_x86/bin/gse_agent',
          'gse/agent_linux_x86/bin/gse_agent',
        ],
      },
    ],
    statistics: {
      success: 1,
      error: 1,
    },
  };
  private selection = 0;
  private importLoading = false;

  private get importDisabled() {
    return this.selection === 0;
  }

  public handleSelectionChange(selection: IAgentHost[]) {
    this.selection = selection.length;
  }
  public handleCancel() {
    this.$router.push({ name: 'agentStatus' });
  }
  public handleLastStep() {
    this.$router.push({ name: 'agentVersion' });
  }
  public handleImport() {
    this.importLoading = true;
    setTimeout(() => {
      this.importLoading = false;
    }, 2000);
  }
  public handleSelectable(row: IAgentHost) {
    return !!row.status;
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

>>> .bk-table-header .bk-table-column-selection .cell {
  @mixin layout-flex row, center, center;
}
>>> .bk-table-body .bk-table-row .bk-table-expand-icon i {
  margin-top: -7px;
}
>>> .bk-table-expanded-cell {
  /* stylelint-disable-next-line declaration-no-important */
  background: #fafbfd !important;

  /* stylelint-disable-next-line declaration-no-important */
  padding: 0 !important;
}
>>> .bk-table th :hover {
  background-color: unset;
  .bk-form-checkbox.is-checked .bk-checkbox {
    background-color: #3a84ff
  }
}
.agent-version-detail {
  .table-header {
    padding: 0 24px;
    margin-bottom: -1px;
    height: 42px;
    background: #f0f1f5;
    border: 1px solid #dcdee5;
    border-radius: 2px 2px 0 0;

    @mixin layout-flex row, center, space-between;
    &-left {
      font-weight: Bold;
      .package-selection {
        color: #979ba5;
      }
    }
    &-right {
      .status-success {
        font-weight: Bold;
        color: #2dcb56;
      }
      .status-error {
        font-weight: Bold;
        color: #ea3636;
      }
    }
  }
  .detail-content {
    padding: 28px 0 24px 101px;
    .detail-row {
      @mixin layout-flex row;
      label {
        color: #b2b5bd;
      }
      &-cell {
        flex-basis: 280px;
        &.file {
          flex: 1;

          @mixin layout-flex row;
          .file-list {
            margin-left: 3px;
          }
        }
      }
    }
  }
  .status-success {
    color: #2dcb56;
  }
  .status-error {
    color: #ea3636;
  }
  .footer {
    text-align: center;
  }
}
</style>
