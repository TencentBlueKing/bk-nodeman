<template>
  <bk-dialog
    ext-cls="pkg-dialog"
    :value="value"
    :width="showOs ? 1048 : 960"
    :position="{ top: 100 }"
    :draggable="$props.operate === 'UPGRADE_AGENT'"
    :mask-close="false"
    :title="title"
    header-position="left"
    @cancel="handleCancel">
    <template slot="header">
      <span class="header">{{ title }}</span>
      <span v-if="operate === 'UPGRADE_AGENT'" class="subTitle">
        <i18n path="已选IP" class="IP-selection">
          <span class="selection-num">{{ num }}</span>
        </i18n>
        <template v-if="selectedVersion">
          <i18n path="升级IP" class="IP-selection">
            <span class="selection-num">，{{ upgrades }}</span>
          </i18n>
          <i18n path="回退IP" class="IP-selection">
            <span class="selection-num">，{{ rollbacks }}</span>
          </i18n>
          <i18n path="已是目标版本Ip" class="IP-selection">
            <span class="selection-num">，{{ nochanges }}</span>
          </i18n>
        </template>
      </span>
      <span v-if="operate === 'reinstall_batch'">
        <i18n path="批量编辑Agent" class="batchEdit">
          <span class="batchSupportOs">{{ allOsVersions }}</span>
        </i18n>
      </span>
    </template>
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
                    content: $props.operate === 'UPGRADE_AGENT'
                      ? row.isLatestVersion ? $t('已是目标版本') : $t('当前版本')
                      : row.isBelowVersion ? $t('版本未处于正式状态') : $t('不能低于当前版本'),
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
        <div class="pkg-desc" :style="{ flex: showOs ? 'initial' : 2 }">
          <p class="title">{{ selectedRow ? $t('pkg的详细信息', [selectedRow.version]) : $t('版本详情') }}</p>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <pre class="content" v-html="markdown" />
        </div>
      </div>
    </div>
    <template slot="footer">
      <bk-button theme="primary" :disabled="disabledClick" @click="handleConfirm">{{ $t('确定') }}</bk-button>
      <bk-button class="ml10" @click="handleCancel">{{ $t('取消') }}</bk-button>
    </template>
  </bk-dialog>
</template>
<script lang="ts">
import { defineComponent, nextTick, ref, toRefs, watch, PropType, computed } from 'vue';
import { AgentStore } from '@/store';
import FlexibleTag from '@/components/common/flexible-tag.vue';
import { IPkgVersion, PkgType } from '@/types/agent/pkg-manage';

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
    versions: {
      type: Array as () => string[],
      default: () => [],
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
    operate: {
      type: String,
      default: '',
    },
    project: {
      type: String as PropType<PkgType>,
      default: 'gse_agent',
    },
  },

  emits: ['input', 'confirm', 'cancel'],
  setup(props, { emit }) {
    const selectedRowRef = ref<any>();

    const loading = ref(false);
    const tableData = ref<any[]>([]);
    const selectedVersion = ref('');
    const selectedRow = ref<IPkgVersion|null>(null);
    const markdown = ref('');
    const lastOs = ref('');
    const defaultVersion = ref('');
    // 当前传入的最高版本
    const currentLatestVersion = ref('');
    
    const num = ref(0);
    const upgrades = ref(0);
    const rollbacks = ref(0);
    const nochanges = ref(0);
    const getPkgVersions = async () => {
      const {
        default_version,
        package_latest_version,
        machine_latest_version,
        pkg_info,
      } = await AgentStore.apiGetPkgVersion({
        // 新增加project的传入
        project: props.project,
        os: props.osType,
        cpu_arch: props.cpuArch,
        versions:props.versions,
      });
      defaultVersion.value = default_version;
      currentLatestVersion.value = machine_latest_version;
      const builtinTags = ['stable', 'latest', 'test'];
      tableData.value.splice(0, tableData.value.length, ...pkg_info.map(item => ({
        ...item,
        disabled: item.disabled || item.version === machine_latest_version,
        isLatestVersion: machine_latest_version === package_latest_version,
        tags: item.tags.filter(tag => builtinTags.includes(tag.name)).map(tag => ({
          className: tag.name,
          description: tag.description,
          name: tag.description,
        })),
      })));
      loading.value = false;
    };
    const disabledClick = computed(() => {
      return !selectedVersion || nochanges.value === props.versions.length;
    });
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

    const handleRowClick = async (row: IPkgVersion) => {
      if (!row.disabled) {
        selectedRow.value = row;
        selectedVersion.value = row.version as string;
        markdown.value = row.description;
        await getCompareVersion(row.version);
      }
    };
    const allOsVersions = ref('');
    const getOs = async () => {
      const list = await AgentStore.apiPkgQuickSearch({ project: 'gse_agent' });
      const osVersions = (list.find(item => item.id === 'os_cpu_arch')?.children || []).reduce((acc, item) => {
        const [os] = item.id.split('_');
        const system = os.charAt(0).toUpperCase() + os.slice(1);
        !acc.includes(system) && acc.push(system);
        return acc;
      }, [] as string[]);
      allOsVersions.value = osVersions.join('、');
    }

    const getCompareVersion = async (version: string) => {
      if(props.operate !== 'UPGRADE_AGENT') return;
      const {
        upgrade_count,
        downgrade_count,
        no_change_count
      } = await AgentStore.apiVersionCompare({
        current_version: version,
        version_to_compares: props.versions,
      });
      upgrades.value = upgrade_count;
      rollbacks.value = downgrade_count;
      nochanges.value = no_change_count;
    }
  
    watch(() => props.value, async (val: boolean) => {
      // val dialog显示隐藏
      if (val) {
        props.operate === 'reinstall_batch' && await getOs();
        num.value = props.versions.length;
        if (lastOs.value !== `${props.osType}_${props.cpuArch}`) {
          loading.value = true;
          selectedRow.value = null;
          await getPkgVersions();
        }
        const selected = props.versions.length >= 1 ? tableData.value.find(row => row.version === props.versions[0]) || null : null;
        if(selected) {
          handleRowClick(selected);
        } else {
          selectedVersion.value = '';
          selectedRow.value = null;
        }
        // 默认选中default_version,已经选过有props.version的就不默认了
        props.versions.length === 0 && defaultVersion && tableData.value.forEach(row=>{
          row.version === defaultVersion.value && handleRowClick(row)
        });
        props.operate === 'UPGRADE_AGENT' && tableData.value.forEach(row=>{
          row.version === currentLatestVersion.value && handleRowClick(row)
        });
      } else {
        lastOs.value = `${props.osType}_${props.cpuArch}`;
        selectedVersion.value = props.versions[0] || '';
        selectedRow.value = tableData.value.find(row => row.version === props.versions[0]) || null;
        if (selectedRow.value) {
          nextTick(() => {
            selectedRowRef.value?.$el.scrollIntoView();
          });
        }
      }
    });

    return {
      ...toRefs(props),
      disabledClick,
      num,
      upgrades,
      rollbacks,
      nochanges,
      selectedRowRef,
      loading,
      tableData,
      selectedVersion,
      selectedRow,
      markdown,
      allOsVersions,
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
.header {
  font-size: 20px;
  color: #313238;
}
span.subTitle:before {
  content: "|";
  margin: 0 13px 0 10px;
  color: #DCDEE5;
}
.IP-selection {
  font-size: 14px;
  color: #63656E;
  letter-spacing: 0;
  .selection-num {
    color: #3A84FF;
    margin: 0 3px;
  }
}
.batchEdit {
  color: #979BA5;
  font-size: 14px;
  margin-left: 29px;
  letter-spacing: 0.5px;
}
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
