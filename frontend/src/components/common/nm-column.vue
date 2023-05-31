<template>
  <bk-table-column
    :prop="prop"
    :show-overflow-tooltip="showOverflowTooltip"
    :render-header="renderHeader || defaultRender"
    v-bind="$attrs"
    v-on="$listeners">
    <template #default="{ row }">
      <slot :row="row">{{ prop ? row[prop] : null }}</slot>
    </template>
  </bk-table-column>
</template>

<script>
export default {
  name: 'NmColumn',
  props: {
    prop: {
      type: String,
      default: '',
    },
    renderHeader: {
      type: Function,
    },
    showOverflowTooltip: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {};
  },
  methods: {
    defaultRender(h, { column }) {
      return h('div', {
        class: 'text-ellipsis',
        directives: [
          { name: 'bk-overflow-tips' },
        ],
      }, column.label);
    },
  },
};
</script>
