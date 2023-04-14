export default {
  name: 'NmPagination',
  props: {
    panelList: {
      type: Array,
      default: () => [],
    },
    value: {
      type: Object as ISelectorValue,
      default: () => ({}),
    },
    action: {
      type: String,
      default: 'strategy_create',
      // type: Array,
      // default: () => [],
    },
  },
  data() {
    return {
      instance: null,
      topology: [],
    };
  },
  computed: {
    isGrayRule() {
      return PluginStore.isGrayRule;
    },
  },
  created() {
  },
  methods: {
    handlePageChange() {
      this.$emit('change', arguments);
    },
    handlePageLimitChange() {
      this.$emit('limit-change', arguments);
    },
  },
  render() {
    return <bk-pagination
      ext-cls="pagination"
      size="small"
      limit={ this.limit }
      count={ this.count }
      current={ this.current }
      limit-list={ this.limitList }
      align="right"
      show-total-count
      selection-count={ this.selectionCount }
      onChange={ this.handlePageChange }
      onLimitChange={ this.handlePageLimitChange } />;
  },
};
