import { DirectiveBinding, DirectiveOptions } from 'vue/types/options';
import { VueConstructor } from 'vue';

interface IValue {
  include: string[] // 需要加滤镜的dom元素
  exclude: string[] // 不被遮罩盖住的元素
  disabled?: boolean // 是否禁用
}

const zIndex = () => {
  // eslint-disable-next-line no-underscore-dangle
  if (window.__bk_zIndex_manager && window.__bk_zIndex_manager.nextZIndex) {
    // eslint-disable-next-line no-underscore-dangle
    return window.__bk_zIndex_manager.nextZIndex();
  }
  return 2000;
};

const toggleFreezingPage = (el: HTMLElement, value: IValue = { include: [], exclude: [] }) => {
  const { include = [], exclude = [], disabled = false } = value;
  const index = zIndex();
  const overlayId = '__freezing_page_id__';

  if (!include.length) {
    el.style.filter = disabled ? 'none' : 'grayscale(1)';
  }
  // 设置或者取消滤镜元素
  include.forEach((selector) => {
    const ele = el.querySelector(selector) as HTMLElement;
    ele && (ele.style.filter = disabled ? 'none' : 'grayscale(1)');
  });
  // 设置或者取消不在遮罩里面元素的z-index
  exclude.forEach((selector) => {
    const ele = el.querySelector(selector) as HTMLElement;
    ele && (ele.style.zIndex = disabled ? 'unset' : index);
  });

  const overlayDom = document.querySelector(`#${overlayId}`) as Node;
  if (!disabled) {
    if (overlayDom) return;

    const overlay = document.createElement('div');
    overlay.id = overlayId;
    overlay.style.zIndex = String(index - 1);
    overlay.style.cssText = 'position: absolute;top: 0;left: 0;'
    + 'background-color: rgba(255,255,255,.4);height: 100%;width: 100%';

    el.style.position = 'relative';
    el.appendChild(overlay);
  } else if (overlayDom) {
    el.removeChild(overlayDom);
  }
};

const freezingPage: DirectiveOptions = {
  inserted(el: HTMLElement, bind: DirectiveBinding) {
    toggleFreezingPage(el, bind.value);
  },
  update(el: HTMLElement, bind: DirectiveBinding) {
    toggleFreezingPage(el, bind.value);
  },
  unbind(el: HTMLElement, bind: DirectiveBinding) {
    toggleFreezingPage(el, bind.value);
  },
};

export default {
  install: (Vue: VueConstructor) => Vue.directive('freezing-page', freezingPage),
  directive: freezingPage,
};
