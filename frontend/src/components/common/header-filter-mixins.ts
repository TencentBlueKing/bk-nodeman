import { Vue, Component } from 'vue-property-decorator';
import { ISearchChild, ISearchItem } from '@/types';
import { toLine } from '@/common/util';

@Component
export default class HeaderFilterMixin extends Vue {
  public filterData: ISearchItem[] = [];
  public searchSelectValue: ISearchItem[] = [];

  // 表头筛选变更
  public tableHeaderConfirm({ prop, list }: { prop: string, list: ISearchChild[] }) {
    const index = this.searchSelectValue.findIndex((item: ISearchItem) => item.id === prop || item.id === toLine(prop));
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
    this.$set(this, 'searchSelectValue', this.searchSelectValue);
  }
  // 表头筛选清空
  public tableHeaderReset({ prop }: { prop: string }) {
    const index = this.searchSelectValue.findIndex(item => item.id === prop);
    if (index > -1) {
      this.searchSelectValue.splice(index, 1);
      this.$set(this, 'searchSelectValue', this.searchSelectValue);
    }
  }
  public handlePushValue(prop: string, values: ISearchChild[], merged = true) {
    if (!values || !Array.isArray(values)) return;
    const index = this.searchSelectValue.findIndex((item: ISearchItem) => item.id === prop || item.id === toLine(prop));
    if (index > -1) {
      const originValues: ISearchChild[] = merged ? this.searchSelectValue[index].values || [] : [];
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
  public handleSearchSelectChange(list: ISearchItem[]) {
    this.filterData.forEach((data) => {
      const item = list.find(item => item.id === data.id);
      if (data.children) {
        data.children = data.children.map((child) => {
          if (!item) {
            child.checked = false;
          } else {
            child.checked = item.values ? item.values.some(value => value.id === child.id) : false;
          }
          return child;
        });
      }
    });
  }
}
