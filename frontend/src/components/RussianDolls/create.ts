export type IInType = 'boolean'|'number'|'string'|'array'|'object'|'json';

interface IItem {
  id: string
  title: string;
  type: IInType;
  required: boolean;
  description: string;
  property: string;
  default: any;
  isAdd: boolean;
  'ui:component': {
    name: string;
    prop: { [key: string]: any };
  };
  properties: IItem;
}

export interface Doll {
  id: string
  type: IInType;

  // formItem
  prop: string;
  title: string; // label & prototype
  property: string; // demo a.0.b.c.2.3
  required: boolean;
  description: string;
  rules?: any[];
  children?: Doll[];

  // 附加的属性
  addAble: boolean; // object array
  deleteAble: boolean; // object array
  convertible: boolean; // 可转换 try JSON.parse // todo
  level: number; // 限制层级深度

  // 表单组件
  component: string;
  props: { [key: string]: any };
  defaultValue: any;

  schema?: any // 原始的配置
  newSchema?: any // 新的配置 todo
}

const lowerStr = 'abcdefghijklmnopqrstuvwxyz0123456789';

export const uuid = (n = 10, str = lowerStr): string => {
  let result = str[parseInt((Math.random() * str.length).toString(), 10)];
  for (let i = 1; i < n; i++) {
    result += str[parseInt((Math.random() * str.length).toString(), 10)];
  }
  return result;
};

const complexType = ['array', 'object'];
const bfArrayTitle = 'labels';
const bfArrayKey = 'key';
const bfArrayValue = 'value';

function getDefaultValue(params) {
  if (params.default) {
    return params.default;
  }
  const { type } = params;
  if (['number', 'string'].includes(type)) {
    return '';
  }
  if (type === 'boolean') {
    return false;
  }
  if (type === 'array') {
    return [];
  }
  return {};
};

function getDefaultComponent(params: IItem) {
  const { type, 'ui:component': component = {} } = params;
  let realComponent = component.name;
  if (type === 'array') {
    const { title, items: { properties = {} } } = params;
    const propKeys = title.includes(bfArrayTitle) ? Object.keys(properties) : [];
    if (propKeys.length === 2 && [bfArrayKey, bfArrayValue].every(key => propKeys.includes(key))) {
      realComponent = 'bfArray';
    }
  } else {
    realComponent = type === 'boolean' ? 'bk-checkbox'  : 'bk-input';
  }
  return realComponent;
};

function getDefaultProps(params: IItem) {
  const { 'ui:component': component = {}, type } = params;
  const prop = component.prop || {};
  if (type === 'number') {
    prop.type = 'number';
  }
  return prop;
};

export function getRules(schema) {
  return schema.required
    ? [
      {
        required: true,
        message: window.i18n.t ? window.i18n.t('必填项') : '必填项',
        trigger: 'blur',
      },
    ]
    : [];
}
export function getAddAble(schema: IItem) {
  return complexType.includes(schema.type);
}
export function getDeleteAble(schema: IItem) {
  return complexType.includes(schema.type);
}
export function getConvertible(schema: IItem) {
  return complexType.includes(schema.type) && !schema.required;
}

export const getRealProp = (parentProp?: string, prop: string): string => (parentProp ? `${parentProp}.${prop}` : prop);

export function formatSchema(schema: IItem, parentProp = '', level = 0): Doll {
  const { type = 'string', properties = {} } = schema;
  const prop = schema.prop || schema.title;
  const property = parentProp ? `${parentProp}.${prop}` : prop;
  // console.log(parentProp, '+', prop, '=', property);
  const baseItem: Doll = {
    id: uuid(),
    type,

    // formItem
    prop,
    title: schema.title || prop,
    property,
    parentProp,
    required: !!schema.required,
    description: schema.description || '',
    rules: getRules(schema),
    children?: null,

    // 附加的属性
    addAble: getAddAble(schema),
    deleteAble: getDeleteAble(schema),
    convertible: getConvertible(schema),
    level,

    // 表单组件
    component: getDefaultComponent(schema),
    props: getDefaultProps(schema),
    defaultValue: getDefaultValue(schema),

    schema, // 原始的配置
    newSchema: {}, // 新的配置 todo
  };
  if (complexType.includes(type)) {
    const newLevel = level + 1;
    if (type === 'array') {
      baseItem.children = [formatSchema(schema.items || {}, `${property}`, newLevel)];
      // properties = schema.items || {}
    } else {
      baseItem.children = Object.keys(properties).map(key => formatSchema(Object.assign({ title: key }, { ...properties[key] }), `${property}`, newLevel));
    }
    // console.log(property, 'cccccccc');
  }
  return baseItem;
}

export function initSchema(schema: IItem): Doll[] {
  // const list: Doll[] = []
  // if (Array.isArray(schema)) {
  //   schema.map((item, index) => list
  // .push(initSchema(item, `${parentProp ? parentProp + '' + index : index}`, level)))
  //   return list
  //   // return schema
  // .map((item, index) => initSchema(item, `${parentProp ? parentProp + '' + index : index}`, level));
  // }
  // console.log(schema.property)
  return formatSchema(schema);
  // return formatSchema(schema, schema.property)
}

export const createItem = (property: string, params: IItem, id?: string): Doll => {
  console.log('property: ', property, params.type, '; params: ', params);
  return {
    id: id || uuid(),
    ...Object.assign({
      property,
      type: 'string',
      required: false,
      readonly: false,
      description: '',
      // default: getDefaultValue(params),
      defautlC: getDefaultValue(params),
      component: getDefaultComponent(params),
      prop: getDefaultProps(params),
      isAdd: false,
      removeAble: false,
      convertible: false,
    }, params),
  };
};
