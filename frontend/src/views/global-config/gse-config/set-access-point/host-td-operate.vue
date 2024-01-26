<template>
  <td>
    <div class="opera-icon-group pl10">
      <i
        v-test="'addRowBtn'"
        :class="['nodeman-icon nc-plus', { 'disable-icon': addDisabled }]"
        @click="() => cellIconClick('add')">
      </i>
      <i
        v-test="'deleteRowBtn'"
        :class="['nodeman-icon nc-minus', { 'disable-icon': deleteDisabled }]"
        @click="() => cellIconClick('delete')">
      </i>
    </div>
  </td>
</template>
<script lang="ts" setup>
import { defineExpose, toRefs } from 'vue';

const props = withDefaults(defineProps<{
  addDisabled: boolean;
  deleteDisabled: boolean;
}>(), {
  addDisabled: false,
  deleteDisabled: false,
});

const emits = defineEmits(['add', 'delete']);

const cellIconClick = (type: 'add' | 'delete') => {
  emits(type);
};

defineExpose({
  ...toRefs(props),
});

</script>

<style lang="postcss">
.opera-icon-group {
    display: flex;
    align-items: center;
    height: 32px;
    font-size: 18px;
    color: #c4c6cc;
    i {
      cursor: pointer;
      &:hover {
        color: #979ba5;
      }
      & + i {
        margin-left: 10px;
      }
      &.disable-icon {
        color: #dcdee5;
        cursor: not-allowed;
      }
    }
  }
</style>
