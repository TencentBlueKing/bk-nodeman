import { MainStore } from '@/store/index';
import { Vue, Component } from 'vue-property-decorator';

// eslint-disable-next-line new-cap
@Component({})
export default class RouterBackMixin extends Vue {
  public routerBack() {
    if (window.history.length <= 1) {
      MainStore.currentNavName
        ? this.$router.push({ name: MainStore.currentNavName })
        : this.$router.push({ path: '/' });
    } else {
      this.$router.back();
    }
  }
}
