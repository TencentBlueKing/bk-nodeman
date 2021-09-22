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
        const [testId, testKey] = value.split('.');
        if (anchorModule?.[testId]) {
          el.setAttribute('data-test-id', `${moduleName}_${anchorModule[testId]}`);
          if (testKey) {
            el.setAttribute('data-test-key', testKey);
          }
        } else {
          window.testAnchor.moduleUnknown.push({ module: moduleName, key: testId });
          console.warn(`not find test anchor: data-test-id="{{${moduleName}.${testId}}}"`);
        }
      },
    });
  }
}
