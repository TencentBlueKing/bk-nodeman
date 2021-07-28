

import { Vue, Component } from 'vue-property-decorator';
import { CreateElement } from 'vue';
import FilterHeader from '@/components/common/filter-header.vue';
import { toLine } from '@/common/util';
import { ISearchItem, ISearchChild, IColumn } from '@/types';
@Component
export default class TableHeaderMixins extends Vue {
  public filterData: ISearchItem[] = [];
  // search select绑定值
  public searchSelectValue: ISearchItem[] = [];

  private get searchSelectData() { // search select数据源
    const ids = this.searchSelectValue.map(item => item.id);
    return this.filterData.filter(item => !ids.includes(item.id));
  }
  private get headerData() { // 表头筛选列表数据源
    return this.filterData.reduce((obj: { [key: string]: ISearchChild[] }, item) => {
      if (item.children && item.children.length) {
        obj[item.id] = item.children;
      }
      return obj;
    }, {});
  }

  // 自定筛选表头
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
  /**
   * search select输入框信息变更
   */
  public handleSearchSelectChange(list: ISearchItem[]) {
    this.filterData.forEach((data) => {
      const item = list.find(item => item.id === data.id);
      if (data.children) {
        data.children = data.children.map((child: ISearchChild) => {
          if (!item) {
            child.checked = false;
          } else {
            child.checked = !!item.values?.some(value => value.id === child.id);
          }
          return child;
        });
      }
    });
  }
  // 表头筛选清空
  public handleFilterHeaderReset(prop: string) {
    const index = this.searchSelectValue.findIndex(item => item.id === prop);
    if (index > -1) {
      this.searchSelectValue.splice(index, 1);
    }
  }
  // 表头筛选变更
  public handleFilterHeaderConfirm(prop: string, list: ISearchChild[]) {
    const index = this.searchSelectValue.findIndex(item => item.id === prop || item.id === toLine(prop));
    const values = list.reduce((pre: ISearchChild[], item) => {
      if (item.checked) {
        pre.push({
          id: item.id,
          name: item.name,
          checked: true,
        });
      }
      return pre;
    }, []);
    if (index > -1) {
      // 已经存在就覆盖
      this.searchSelectValue[index].values = values;
    } else {
      const data = this.filterData.find(data => data.id === prop || data.id === toLine(prop));
      // 不存在就添加
      this.searchSelectValue.push({
        id: prop,
        name: data ? data.name : '',
        values,
      });
    }
  }
  public handlePushValue(prop: string, values: ISearchChild[], merged = true) {
    if (!values || !Array.isArray(values)) return;
    const index = this.searchSelectValue.findIndex(item => item.id === prop || item.id === toLine(prop));
    if (index > -1) {
      const originValues = merged ? this.searchSelectValue[index].values || [] : [];
      values.forEach((value) => {
        const isExist = originValues.some((item: ISearchChild) => item && item.id === value.id);
        if (!isExist) {
          originValues.push(value);
        }
      });
      this.searchSelectValue[index].values = originValues;
    } else if (prop) {
      const data = this.filterData.find(data => data.id === prop || data.id === toLine(prop));
      this.searchSelectValue.push({
        id: prop,
        name: data ? data.name : '',
        values,
      });
    }
  }
}
