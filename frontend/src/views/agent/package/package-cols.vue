<template>
  <!-- :max-height="windowHeight - 220" -->
  <bk-table
    class="pkg-manage-table"
    :data="rows">
    <NmColumn :label="$t('包名称')" prop="pkg_name" min-width="210" fixed />
    <NmColumn :label="$t('版本号')" prop="version" min-width="120" sortable />
    <NmColumn :label="$t('操作系统/架构')" prop="sys" min-width="120">
      <template #default="{ row }">
        {{ `${row.os}_${row.cpu_arch}` }}
      </template>
    </NmColumn>
    <NmColumn :label="$t('标签信息')" prop="tags" min-width="200" :show-overflow-tooltip="false">
      <template #default="{ row }">
        <FlexibleTag :list="row.formatTags" />
      </template>
    </NmColumn>
    <NmColumn :label="$t('上传用户')" prop="created_by" min-width="120" />
    <NmColumn :label="$t('上传时间')" prop="created_time" class-name="config-cell" min-width="150" />
    <NmColumn :label="$t('已部署主机')" prop="hostNumber" min-width="120" align="right">
      <template #default="{ row }">
        <span v-if="row.hostNumber" class="nm-link" @click="goAgentStatus(row)">{{ row.hostNumber }}</span>
        <span v-else>0</span>
      </template>
    </NmColumn>
    <NmColumn :label="$t('状态')" prop="is_ready" min-width="90" align="center">
      <template #default="{ row }">
        <span :class="['tag-switch', { 'tag-enable': row.is_ready }]">
          {{ row.is_ready ? $t('启用') : $t('停用')}}
        </span>
      </template>
    </NmColumn>
    <NmColumn :label="$t('操作')" prop="message" min-width="100" fixed="right">
      <template #default="{ row }">
        <bk-button text theme="primary" :disabled="btnLoading[row.id]" @click="rowOperate(row)">
          {{ row.is_ready ? $t('停用') : $t('启用')}}
        </bk-button>
        <bk-button
          v-if="!row.is_ready"
          class="ml10"
          text
          theme="primary"
          :disabled="btnLoading[row.id]"
          @click="rowOperate(row, 'delete')">
          {{ $t('删除') }}
        </bk-button>
      </template>
    </NmColumn>
  </bk-table>
</template>
<script lang="ts">
import i18n from '@/setup';
import { AgentStore } from '@/store';
import { PropType, defineComponent, getCurrentInstance, reactive, toRefs } from 'vue';
import FlexibleTag from '@/components/common/flexible-tag.vue';
import { IPkgRow } from '@/types/agent/pkg-manage';

export default defineComponent({
  components: {
    FlexibleTag,
  },
  props: {
    rows: {
      type: Array as PropType<IPkgRow[]>,
      default: () => [],
    },
  },
  emits: ['pagetion'],
  setup(props, { emit }) {
    const { proxy } = (getCurrentInstance() || {});
    const state = reactive<{
      activeRow: Pick<IPkgRow, 'id'|'is_ready'>,
      btnLoading: Partial<{ [id: string]: boolean; }>
    }>({
      activeRow: {
        id: -1,
        is_ready: false,
      },
      // operateType: <string>'',
      btnLoading: {},
    });
    const switchPkgStatus = async () => {
      const isReady = !state.activeRow.is_ready;
      const res = await AgentStore.apiPkgUpdateStatus({ id: state.activeRow.id, is_ready: isReady });
      if (res?.id) {
        state.activeRow.is_ready = isReady;
        proxy?.$bkMessage({
          theme: 'success',
          message: isReady ? i18n.t('启用成功') : i18n.t('停用成功'),
        });
      }
    };
    const detelePkg = async () => {
      const res = await AgentStore.apiPkgDelete(state.activeRow.id);
      if (res) {
        proxy?.$bkMessage({
          theme: 'success',
          message: i18n.t('删除成功'),
        });
        emit('pagetion');
      }
    };
    const rowOperate = async (row: IPkgRow, type = 'toggle') => {
      state.activeRow = row;
      if (type === 'toggle') {
        if (row.is_ready) {
          proxy?.$bkInfo({
            title: i18n.t('确认停用该Agent包'),
            subHeader: proxy?.$createElement('div', {}, [
              proxy?.$createElement('p', {}, i18n.t('确认停用该Agent包Tip1', [row.pkg_name])),
              proxy?.$createElement('p', {}, i18n.t('确认停用该Agent包Tip2')),
            ]),
            // proxy?.$tc('确认停用该Agent包Tip', [row.pkg_name]),
            extCls: 'wrap-title',
            confirmFn: switchPkgStatus,
          });
          return;
        }
        switchPkgStatus();
      } else {
        proxy?.$bkInfo({
          title: i18n.t('确认删除该Agent包'),
          subHeader: proxy?.$createElement('div', {}, [
            proxy?.$createElement('p', {}, i18n.t('确认删除该Agent包Tip1', [row.pkg_name])),
            proxy?.$createElement('p', {}, i18n.t('确认删除该Agent包Tip2')),
          ]),
          extCls: 'wrap-title',
          confirmFn: detelePkg,
        });
      }
    };
    const goAgentStatus = (row: IPkgRow) => {
      proxy?.$router.push({
        name: 'agentStatus',
        params: {
          os_type: row.os,
          version: row.version,
        },
      });
    };

    return {
      ...toRefs(props),
      ...toRefs(state),
      rowOperate,
      goAgentStatus,
    };
  },
});
</script>
<style lang="postcss">
@import "@/css/variable.css";

.pkg-manage-table {
  .flexible-tag-group .tag-item {
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
</style>
