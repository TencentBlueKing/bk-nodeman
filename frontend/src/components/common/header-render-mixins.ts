import { Vue, Component, Emit } from 'vue-property-decorator';
import FilterHeader from '@/components/common/filter-header.vue';
import { ISearchItem, ISearchChild, IColumn } from '@/types';
import { toLine } from '@/common/util';
import { CreateElement } from 'vue';

@Component
export default class TableHeaderRenderMixin extends Vue {
  public filterData: ISearchItem[] = [];

  // 表头筛选列表数据源
  private get headerData() {
    return this.filterData.reduce((obj: { [key: string]: ISearchChild[] }, item: ISearchItem) => {
      if (item.children && item.children.length) {
        obj[item.id] = item.children;
      }
      return obj;
    }, {});
  }

  // eslint-disable-next-line new-cap
  @Emit('filter-confirm')
  public handleFilterHeaderConfirm(prop: string, list: ISearchChild[]) {
    this.handleFilterChange({ prop, list });
    return { prop, list };
  }
  // eslint-disable-next-line new-cap
  @Emit('filter-reset')
  public handleFilterHeaderReset(prop: string) {
    this.handleFilterChange({ prop });
    return { prop };
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  public handleFilterChange(param: { prop: string, list?: ISearchChild[] }) {}
  public renderFilterHeader(h: CreateElement, data: IColumn) {
    const filterList = this.headerData[data.column.property] || this.headerData[toLine(data.column.property)] || [];
    const item = this.filterData.find((item) => {
      const { property } = data.column;
      return item.id === property || item.id === toLine(property);
    });
    const title = data.column.label || '';
    const property = data.column.property || '';

    return h(FilterHeader, {
      props: {
        name: title,
        property,
        width: item?.width,
        align: item?.align,
        filterList,
        checkAll: !!item?.showCheckAll,
        showSearch: !!item?.showSearch,
      },
      on: {
        confirm: ({ prop, list }: { prop: string, list: ISearchChild[] }) => this.handleFilterHeaderConfirm(prop, list),
        reset: (prop: string) => this.handleFilterHeaderReset(prop),
      },
    });
  }
}
