import { Vue, Component } from 'vue-property-decorator';

@Component
export default class Emitter extends Vue {
  public dispatch(componentName: string, eventName: string, params?: any) {
    let parent = this.$parent || this.$root;
    let { name } = parent.$options;

    while (parent && (!name || name !== componentName)) {
      parent = parent.$parent;

      if (parent) {
        name = parent.$options.name;
      }
    }
    if (parent) {
      parent.$emit.apply<Vue, any, void>(parent, [...[eventName].concat(params)]);
    }
  }
}
