import { Component, Vue } from 'vue-property-decorator';
import { MainStore } from '@/store/index';

Component.registerHooks([
  'beforeRouteEnter',
]);
// eslint-disable-next-line new-cap
export default () => Component(class authorityMixin extends Vue {
  public authority: {[propsName: string]: boolean} = {
    operate: true,
  };
  public beforeRouteEnter(to: any, from: any, next: any) {
    next((vm: any) => {
      vm.handleInitPageAuthority(to.meta?.authority?.operate);
    });
  }
  public async handleInitPageAuthority(action: string) {
    if (!action || !MainStore.permissionSwitch) return;
    const list = await MainStore.getBkBizPermission({ action });
    this.authority.operate = Array.isArray(list) ? !!list.length : true;
  }
});

