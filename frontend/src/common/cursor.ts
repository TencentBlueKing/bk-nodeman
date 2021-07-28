import { DirectiveBinding, DirectiveOptions } from 'vue/types/options';
import { VueConstructor } from 'vue';

interface IElement extends HTMLElement {
  __cursor__: any
  // eslint-disable-next-line camelcase
  __cursor_target__: any
}

interface IOptions {
  x: number
  y: number
  width: number
  height: number
  zIndex: number
  cursor: string
  className: string
  activeClass: string
  active?: boolean
  selector?: string
}

const requestFrame = window.requestAnimationFrame
    || window.mozRequestAnimationFrame
    || window.webkitRequestAnimationFrame
    || function (fn) {
      return window.setTimeout(fn, 20);
    };

const cancelFrame = window.cancelAnimationFrame
    || window.mozCancelAnimationFrame
    || window.webkitCancelAnimationFrame
    || window.clearTimeout;

const addEventListener = (el: IElement) => {
  el.addEventListener('mouseenter', mouseenter);
  el.addEventListener('mousemove', mousemove);
  el.addEventListener('mouseleave', mouseleave);
  el.addEventListener('click', click);
};
const removeEventListener = (el: IElement) => {
  el.removeEventListener('mouseenter', mouseenter);
  el.removeEventListener('mousemove', mousemove);
  el.removeEventListener('mouseleave', mouseleave);
  el.removeEventListener('click', click);
};

const options: IOptions = {
  x: 12,
  y: 8,
  width: 16,
  height: 16,
  zIndex: 100000,
  cursor: 'pointer',
  className: 'v-cursor',
  activeClass: 'v-cursor-active',
};

const mouseenter = (event: MouseEvent) => {
  const el = event.currentTarget as IElement;
  const data = el.__cursor__;
  if (data.active) {
    el.style.cursor = data.cursor;
    proxy.style.display = 'block';
    el.classList.add(data.activeClass);
    updateProxyPosition(event);
  }
};

const mousemove = (event: MouseEvent) => {
  const el = event.currentTarget as IElement;
  const data = el.__cursor__;
  if (data.active) {
    updateProxyPosition(event);
  }
};

const mouseleave = (event: MouseEvent) => {
  const el = event.currentTarget as IElement;
  const data = el.__cursor__;
  el.style.cursor = '';
  proxy.style.display = 'none';
  el.classList.remove(data.activeClass);
};

const click = (event: MouseEvent) => {
  const el = event.currentTarget as IElement;
  const data = el.__cursor__;
  if (!data.active) {
    return false;
  }
  const callback = data.onclick;
  if (typeof callback === 'function') {
    callback(data);
  }
  const { globalCallback } = data;
  if (typeof globalCallback === 'function') {
    globalCallback(data);
  }
};

let proxy: HTMLElement;
let frameId: any = null;

const createProxy = () => {
  proxy = document.createElement('span');
  proxy.style.position = 'fixed';
  proxy.style.pointerEvents = 'none';
  proxy.style.zIndex = String(options.zIndex);
  proxy.style.width = `${options.width}px`;
  proxy.style.height = `${options.height}px`;
  proxy.classList.add(options.className);
  document.body.append(proxy);
};

const updateProxyPosition = (event: MouseEvent) => {
  const el = event.currentTarget as IElement;
  const data = el.__cursor__;
  if (frameId) {
    cancelFrame(frameId);
  }
  frameId = requestFrame(() => {
    proxy.style.left = `${event.clientX + data.x}px`;
    proxy.style.top = `${event.clientY + data.y}px`;
  });
};

const setChildrenEvents = (target: IElement, pointerEvents: string) => {
  Array.prototype.forEach.call(target.children, (child) => {
    child.style.pointerEvents = pointerEvents;
  });
};

const cursor: DirectiveOptions = {
  inserted(el: HTMLElement, binding: DirectiveBinding) {
    if (!proxy) {
      createProxy();
    }
    const data = { ...options };
    if (typeof binding.value !== 'object') {
      data.active = binding.value;
    } else {
      Object.assign(data, binding.value);
    }
    const target = (data.selector ? el.querySelector(data.selector) : el) as IElement;
    if (target) {
      (el as IElement).__cursor_target__ = target;
      target.__cursor__ = data;
      addEventListener(target);
      const pointerEvents = data.active ? 'none' : '';
      setChildrenEvents(target, pointerEvents);
    }
  },
  update(el, binding) {
    const data = { ...options };
    if (typeof binding.value !== 'object') {
      data.active = binding.value;
    } else {
      Object.assign(data, binding.value);
    }
    let target = (el as IElement).__cursor_target__;
    if (!target) {
      target = el.querySelector(data.selector as string);
      if (target) {
        (el as IElement).__cursor_target__ = target;
        target.__cursor__ = data;
        addEventListener(target);
        const pointerEvents = data.active ? 'none' : '';
        setChildrenEvents(target, pointerEvents);
      }
    } else {
      Object.assign(target.__cursor__, data);
      const pointerEvents = data.active ? 'none' : '';
      setChildrenEvents(target, pointerEvents);
    }
  },
  unbind(el: HTMLElement) {
    const target = (el as IElement).__cursor_target__;
    removeEventListener(target);
  },
};

export default {
  install: (Vue: VueConstructor) => Vue.directive('cursor', cursor),
  directive: cursor,
  setOptions: (customOptions: IOptions) => {
    Object.assign(options, customOptions);
  },
};
