import { DirectiveBinding } from 'vue/types/options';
import testAnchorMap from '@/config/test-anchor-key';
import { VNode, VueConstructor } from 'vue/types/umd';

const modulesMap = {};
const all = [];
const moduleNames = Object.keys(testAnchorMap);
moduleNames.forEach((moduleName) => {
  modulesMap[moduleName] = Array.from(Object.values(testAnchorMap[moduleName])).map(item => `${moduleName}_${item}`);
  all.push(...modulesMap[moduleName]);
});

window.testAnchor = {
  moduleMap: testAnchorMap,
  moduleSet: modulesMap,
  moduleUnknown: [],
  all,
};

export default class TestAnchorDirective {
  public static install(Vue: VueConstructor) {
    Vue.directive('test', {
      bind(el: IElement, { value, modifiers }: DirectiveBinding, { context }: VNode) {
        const moduleName = moduleNames.find(key => modifiers[key]) || context.$route.name;
        const anchorModule = testAnchorMap[moduleName];
        if (anchorModule?.[value]) {
          el.setAttribute('data-test-id', `${moduleName}_${anchorModule[value]}`);
        } else {
          window.testAnchor.moduleUnknown.push({ module: moduleName, key: value });
          console.warn(`not find test anchor: data-test-id="{{${moduleName}.${value}}}"`);
        }
      },
    });
  }
}
