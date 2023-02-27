import { Vue, Component } from 'vue-property-decorator';

@Component({ EmptyMixin })
class EmptyMixin extends Vue {
  public emptySearchClear(): void {
    this.$emit('empty-clear');
  }
  public emptyRefresh(): void {
    this.$emit('empty-refresh');
  }
}

Vue.mixin(EmptyMixin);
