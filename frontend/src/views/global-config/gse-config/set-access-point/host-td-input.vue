<template>
  <td class="is-required">
    <VerifyInput
      ref="checkItem"
      required
      position="right"
      error-mode="mask"
      :rules="rules"
      :default-validator="getDefaultValidator()">

      <InstallInputType
        type="text"
        :input-value="value"
        :placeholder="$t('请输入')"
        :disabled="disabled"
        v-test="'apBaseInput'"
        @update="tdInput">
      </InstallInputType>

    </VerifyInput>
  </td>
</template>
<script lang="ts" setup>
import { ref, toRefs } from 'vue';
import { MainStore } from '@/store/index';
import VerifyInput from '@/components/common/verify-input.vue';
import InstallInputType from '@/components/setup-table/install-input-type.vue';
import { TranslateResult } from 'vue-i18n';

const props = withDefaults(defineProps<{
  value: string;
  disabled: boolean;
  rules: {
    // trigger?: string;
    message: TranslateResult;
    validator: (val: string, index: number) => boolean
  }[]
}>(), {
  value: '',
  disabled: false,
  rules: () => [],
});

const emits = defineEmits(['input', 'change']);

const checkItem = ref();

const getDefaultValidator = () => ({
  show: false,
  message: '',
  errTag: true,
});

const tdInput = (value: string) => {
  MainStore.updateEdited(true);
  const valTrim = value.trim();
  emits('input', valTrim);
  emits('change', valTrim);
};
const handleValidate = (cb: () => { show: boolean }) => checkItem.value?.handleValidate(cb);

defineExpose({
  ...toRefs(props),
  checkItem,
  handleValidate,
});

</script>
<style lang="postcss">
</style>
