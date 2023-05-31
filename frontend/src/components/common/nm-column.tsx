import { IColumn } from '@/types';

export default {
  name: 'NmColumn',
  props: {
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
    defaultRender(h: CreateElement, { column }: IColumn) {
      console.log(column);
      return <div v-bk-overflow-tips>{ column.label }</div>;
    },
  },
  render() {
    console.log(this.$attrs, this.props);
    return <bk-table-column
      show-overflow-tooltip={ this.showOverflowTooltip }
      renderHeader={ this.renderHeader || this.defaultRender}
      attrs={this.$attrs}
      scopedSlots={{
        default: proxy => this.$scopedSlots.default(proxy),
      }} />;
  },
};
