<template>
  <bk-dialog
    ext-cls="pkg-dialog"
    :value="value"
    :width="showOs ? 1048 : 960"
    :position="{ top: 100 }"
    :draggable="false"
    :mask-close="false"
    :title="title"
    header-position="left"
    @cancel="handleCancel">
    <div class="pkg-version-wrapper">
      <ul class="os-list" v-if="showOs">
        <li
          :class="['os-item', { active: `${osType}_${cpuArch}` === os.id }]"
          v-for="os in osVersions" :key="os.os_type">
          <div class="os-info">
            <i :class="`os-icon nodeman-icon nc-${os.os_type}`" />
            <span>{{ os.name }}</span>
          </div>
          <span class="nm-tag os-version" v-if="os.version">{{ os.version }}</span>
        </li>
      </ul>
      <div class="pkg-wrapper" v-bkloading="{ isLoading: loading }">
        <div class="pkg-table-wrapper">
          <bk-table
            class="pkg-table"
            height="100%"
            :data="tableData"
            :outer-border="false"
            :row-class-name="handleRowClass"
            @row-click="handleRowClick">
            <bk-table-column width="34">
              <template #default="{ row }">
                <bk-radio
                  :ref="selectedVersion === row.version ? 'selectedRowRef' : ''"
                  :disabled="row.disabled"
                  :value="selectedVersion === row.version"
                  width="90"
                  v-bk-tooltips.left="{
                    content: row.isBelowVersion ? $t('版本未处于正式状态') : $t('不能低于当前版本'),
                    disabled: !row.disabled
                  }">
                </bk-radio>
              </template>
            </bk-table-column>
            <NmColumn :label="$t('Agent 版本')" sortable prop="version" :show-overflow-tooltip="false">
              <template #default="{ row }">
                <span class="version">{{ row.version || '--' }}</span>
                <FlexibleTag v-if="row.tags.length" :list="row.tags" />
              </template>
            </NmColumn>
            <NmColumn width="20" resizable>
              <template #default="{ row }">
                <i class="bk-icon icon-right-shape active-arrow" v-show="selectedVersion === row.version"></i>
              </template>
            </NmColumn>
          </bk-table>
        </div>
        <div class="pkg-desc">
          <p class="title">{{ selectedRow ? $t('pkg的详细信息', [selectedRow.version]) : $t('版本详情') }}</p>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <pre class="content" v-html="markdown" />
        </div>
      </div>
    </div>
    <template slot="footer">
      <bk-button theme="primary" :disabled="!selectedVersion" @click="handleConfirm">{{ $t('确定') }}</bk-button>
      <bk-button class="ml10" @click="handleCancel">{{ $t('取消') }}</bk-button>
    </template>
  </bk-dialog>
</template>
<script lang="ts">
import { defineComponent, nextTick, ref, toRefs, watch } from 'vue';
import { AgentStore } from '@/store';
import FlexibleTag from '@/components/common/flexible-tag.vue';
import { IPkgVersion } from '@/types/agent/pkg-manage';

export default defineComponent({
  name: 'ChoosePkgDialog',
  components: {
    FlexibleTag,
  },
  props: {
    value: {
      default: false,
      type: Boolean,
    },
    type: {
      type: String,
      default: '',
    },
    showOs: {
      type: Boolean,
      default: false,
    },
    version: {
      type: String,
      default: '',
    },
    osType: {
      type: String,
      default: '',
    },
    cpuArch: {
      type: String,
      default: '',
    },
    osVersions: {
      type: Array,
      default: () => [],
    },
    title: {
      type: String,
      default: '',
    },
  },

  emits: ['input', 'confirm', 'cancel'],
  setup(props, { emit }) {
    const selectedRowRef = ref<any>();

    const loading = ref(false);
    const tableData = ref<IPkgVersion[]>([]);
    const selectedVersion = ref('');
    const selectedRow = ref<IPkgVersion|null>(null);
    const markdown = ref('');
    const lastOs = ref('');
    const defaultVersion = ref('');

    const getPkgVersions = async () => {
      const {
        default_version,
        pkg_info,
      } = await AgentStore.apiGetPkgVersion({
        project: 'gse_agent',
        os: props.osType || '',
        cpu_arch: props.cpuArch || ''
      });
      defaultVersion.value = default_version;
      const builtinTags = ['stable', 'latest', 'test'];
      tableData.value.splice(0, tableData.value.length, ...pkg_info.map(item => ({
        ...item,
        tags: item.tags.filter(tag => builtinTags.includes(tag.name)).map(tag => ({
          className: tag.name,
          description: tag.description,
          name: tag.description,
        })),
      })));
      loading.value = false;
    };

    const handleConfirm = () => {
      emit('confirm', {
        osType: props.osType,
        cpuArch: props.cpuArch,
        ...selectedRow.value,
      });
      emit('input', false);
    };
    const handleCancel = () => {
      selectedRow.value = null;
      emit('input', false);
      emit('cancel');
    };

    // 参考 部署策略 - 选择插件版本
    const handleRowClass = ({ row }: {row: IPkgVersion}) => {
      if (row.disabled) {
        return 'row-disabled';
      }
      if (row.version === selectedVersion.value) {
        return 'row-active';
      }
    };

    const handleRowClick = (row: IPkgVersion) => {
      if (!row.disabled) {
        selectedRow.value = row;
        selectedVersion.value = row.version as string;
        markdown.value = row.description;
      }
    };

    watch(() => props.value, async (val: boolean) => {
      if (val) {
        if (lastOs.value !== `${props.osType}_${props.cpuArch}`) {
          loading.value = true;
          selectedRow.value = null;
          await getPkgVersions();
        }
        const selected = props.version ? tableData.value.find(row => row.version === props.version) || null : null;
        selected && handleRowClick(selected);
        // 默认选中default_version,已经选过有props.version的就不默认了
        props.version === '' && defaultVersion && tableData.value.forEach(row=>{
          row.version === defaultVersion.value && handleRowClick(row)
        })
      } else {
        lastOs.value = `${props.osType}_${props.cpuArch}`;
        selectedVersion.value = props.version;
        selectedRow.value = tableData.value.find(row => row.version === props.version) || null;
        if (selectedRow.value) {
          nextTick(() => {
            selectedRowRef.value?.$el.scrollIntoView();
          });
        }
      }
    });

    return {
      ...toRefs(props),
      selectedRowRef,
      loading,
      tableData,
      selectedVersion,
      selectedRow,
      markdown,
      handleConfirm,
      handleCancel,
      handleRowClass,
      handleRowClick,
    };
  },
});
</script>
<style lang="postcss">
@import "@/css/variable.css";

.pkg-version-wrapper {
  display: flex;
  height: 490px;
  /* left */
  .os-list {
    margin-right: 12px;
    padding: 8px 0;
    width: 274px;
    flex-shrink: 0;
    background: #f5f7fa;
    border-radius: 2px 2px 0 0;
    overflow-y: auto;
    .os-item {
      position: relative;
      padding: 0 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 36px;
      &.active {
        color: #3a84ff;
        background-color: #e1ecff;
        .os-version {
          background-color: #3a84ff;
        }
      }
    }
    .os-info {
      display: flex;
      align-items: center;
    }
    .os-icon {
      margin-right: 4px;
    }
    .os-version {
      padding: 0 4px;
      min-width: 44px;
      height: 16px;
      line-height: 16px;
      text-align: center;
      background-color: #979ba5;
      color: #fff;
    }
  }

  .pkg-wrapper {
    flex: 1;
    display: flex;
    width: 714px;
    border: 1px solid #dcdee5;
    border-bottom: 0;
  }

  /* center */
  .pkg-table-wrapper {
    flex: 1;
    width: 285px;
  }
  .pkg-table {
    width: 100%;
    .active-arrow {
      color: #979ba5;
    }
  }

  /* right */
  .pkg-desc {
    width: 425px;
    display: flex;
    flex-direction: column;
    border-left: 1px solid #dcdee5;
    z-index: 0;
    .title {
      height: 43px;
      line-height: 43px;
      padding-left: 22px;
      background: #fafbfd;
      border-bottom: 1px solid #dcdee5;
      font-size: 14px;
      color: #313238;
    }
    .content {
      border: 0;
      height: 100%;
      margin: 0;
      padding: 16px;
      font-size: 12px;
      line-height: 24px;
      white-space: pre-line;
      overflow-x: hidden;
      overflow-y: auto;
    }
  }
  .flexible-tag-group {
    margin-left: 2px;
    .tag-item {
      &.stable {
        color: #14a568;
        background-color: #e4faf0;
      }
      &.latest {
        color: $primaryFontColor;
        background-color: #edf4ff;
      }
      &.test {
        color: #fe9c00;
        background-color: #fff1db;
      }
    }
  }

  .bk-table-header {
    th {
      background-color: #fafbfd;
    }
  }
  .bk-table-body {
    tr {
      cursor: pointer;
      &.row-disabled {
        cursor: not-allowed;
      }
    }
    tr:hover {
      background-color: #f0f1f5 !important;
    }
    tr:hover>td {
      background-color: #f0f1f5 !important;
    }
    .row-active {
      background-color: #f0f1f5;
      .tag-enable {
        background: #d6e7da;
      }
    }
    td .cell {
      padding: 0 13px;
      display: flex;
      line-height: 22px;
      .version{
        min-width: fit-content;
      }
    }
    td:first-child .cell {
      padding-right: 0;
    }
    td.is-last .cell {
      padding: 0;
    }
    .tag-yellow {
      height: 18px;
      line-height: 18px;
    }
  }
}
.pkg-dialog .bk-dialog-body {
  padding: 0 24px;
}

</style>
