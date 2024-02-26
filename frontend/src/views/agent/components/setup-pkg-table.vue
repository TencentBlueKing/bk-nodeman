<template>
  <div class="setup-pkg-table install-table-wrapper ">
    <!-- 表头 -->
    <section class="install-table-header">
      <div class="table-header">
        <table class="form-table">
          <colgroup>
            <col width="auto">
            <col width="400">
          </colgroup>

          <thead>
            <tr>
              <th>
                <div class="cell">{{ $t('操作系统') }}</div>
              </th>
              <th>
                <div class="cell">
                  <TableHeader
                    required
                    batch
                    algin="left"
                    is-batchicon-show
                    :label="$t('包版本')"
                    parent-prop="xx"
                    @confirm="handleBatchConfirm(arguments, config)">
                  </TableHeader>
                </div>
              </th>
            </tr>
          </thead>

          <tbody class="table-body">
            <tr v-for="(row, rowIndex) in tableData" :key="rowIndex">
              <td>
                <div class="os-td">{{ row.name }}</div>
              </td>
              <td>
                <VerifyInput
                  required
                  position="right"
                  error-mode="mask"
                  prop="version"
                  :id="row.id"
                  :icon-offset="10"
                  :ref="(el) => verifyRefs[rowIndex] = el"
                  :default-validator="getDefaultValidator(row)">
                  <InstallInputType
                    v-model="row.version"
                    v-bind="{
                      clearable: false,
                      prop: 'version',
                      type: 'choose',
                      wrapperBorder: true,
                      placeholder: $t('请选择')
                    }"
                    @choose="() => handleChoose(row)"
                    @change="() => handleChange(rowIndex)">
                    <div slot="choose" style="display: flex; align-items: center; height: 100%;">
                      {{ row.version }}
                      <FlexibleTag v-if="row.tags.length" :list="row.tags" style="margin-left: 6px;" />
                    </div>
                  </InstallInputType>
                </VerifyInput>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref, toRefs } from 'vue';
import VerifyInput from '@/components/common/verify-input.vue';
import TableHeader from '@/components/setup-table/table-header.vue';
import InstallInputType from '@/components/setup-table/install-input-type.vue';
import FlexibleTag from '@/components/common/flexible-tag.vue';
import i18n from '@/setup';

export default defineComponent({
  name: 'SetupPkgTable',
  components: {
    VerifyInput,
    TableHeader,
    InstallInputType,
    FlexibleTag,
  },
  props: {
    tableData: {
      type: Array,
      default: () => ([]),
    },
  },
  emits: ['choose'],
  setup(props, { emit }) {
    const verifyRefs = ref<any[]>([]);

    const loaded = ref(false);
    const handleBatchConfirm = () => {};
    const getDefaultValidator = row => ({
      show: loaded.value ? !row.version : false,
      message: i18n.t('必填项'),
    });
    const handleChoose = (row) => {
      emit('choose', { type: 'by_system_arch', ...row });
    };
    const handleChange = (index: number) => {
      verifyRefs.value[index]?.handleUpdateDefaultValidator();
    };

    const validate = () => {
      const isValidate = props.tableData.every(row => row.version);
      verifyRefs.value.forEach((verifyInputRef) => {
        verifyInputRef.handleUpdateDefaultValidator?.();
      });
      return isValidate;
    };

    onMounted(() => {
      loaded.value = true;
    });

    return {
      ...toRefs(props),
      verifyRefs,

      handleBatchConfirm,
      handleChoose,
      handleChange,
      getDefaultValidator,
      validate,
    };
  },
});
</script>

<style lang="postcss">
@import "@/css/variable.css";

.setup-pkg-table {
  border-bottom: 1px solid #dcdee5;
  th {
    padding-left: 8px!important;
    text-align: left;
  }
  line-height: 42px;
  td:first-child {
    padding: 0 8px;
    background-color: #fafbfd;
  }

  .flexible-tag-group {
    display: inline-flex;
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
}
</style>
